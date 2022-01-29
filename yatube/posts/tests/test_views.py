# deals/tests/test_views.py
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.group_new = Group.objects.create(
            title='Новый тестовый заголовок',
            description='Новое тестовое описание',
            slug='new-test-slug'
        )
        cls.user = User.objects.create_user(
            username='username'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_page_uses_correct_template(self):
        """URL-адрес использует соответствующий html-шаблон"""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={
                        'post_id': self.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}): 'posts/create_post.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        post_in_page = response.context['page_obj'][0]
        self.assertEqual(post_in_page.text, self.post.text)
        self.assertEqual(post_in_page.author.username, self.user.username)
        self.assertEqual(post_in_page.group.title, self.group.title)

    def test_group_post_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        post_in_page = response.context['page_obj'][0]
        self.assertEqual(post_in_page.group.title, self.group.title)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': self.user})
        )
        post_in_page = response.context['page_obj'][0]
        self.assertEqual(post_in_page.author.username, self.user.username)
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным коктекстом."""
        response = self.guest_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        post_in_page = response.context['post']
        self.assertEqual(post_in_page.id, self.post.id)
        self.assertEqual(post_in_page.author.username, self.user.username)

    # Проверка словаря контекста страницы создания поста
    # и его редактирования (в нём передаётся форма)
    def test_create_and_edit_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response1 = self.authorized_client.get(reverse('posts:post_create'))
        response2 = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field1 = response1.context.get('form').fields.get(value)
                form_field2 = response2.context.get('form').fields.get(value)
                self.assertIsInstance(form_field1, expected)
                self.assertIsInstance(form_field2, expected)

    def test_post_in_pages(self):
        """Проверка: если указать группу,
           пост появляется на ожидаемых страницах."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.context['page_obj'][0], self.post)
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_new_group_post(self):
        """Проверка: пост не попадает в группу, для которой не предназначен."""
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(
            len(response.context['page_obj']), self.group.posts.count()
        )
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_new.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_images_appears_in_pages(self):
        """При выводе поста с картинкой
           изображение появлется на нужных страницах."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        self.post_with_picture = Post.objects.create(
            author=self.user,
            text='Новый текст с картинкой',
            group=self.group,
            image=uploaded
        )
        urls = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.user}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        for url in urls:
            with self.subTest(url=url):
                self.guest_client.get(url)
                self.assertEqual(Post.objects.count(), posts_count + 1)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.user = User.objects.create_user(
            username='username'
        )
        cls.posts_count = 13
        cls.objects = [Post(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group)
            for _ in range(cls.posts_count)
        ]
        Post.objects.bulk_create(cls.objects, cls.posts_count)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        """Проверка: количество постов на первой странице равна 10."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']), settings.NUMBER_POSTS)

    def test_second_page_contains_three_records(self):
        """Проверка: количество постов на второй странице равна 3"""
        response = self.guest_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         self.posts_count % settings.NUMBER_POSTS)

    def test_first_page_group_list(self):
        """Проверка: первая страница группы сожержит 10 постов."""
        response = self.guest_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(
            len(response.context['page_obj']), settings.NUMBER_POSTS)

    def test_first_page_profile(self):
        """Проверка: страница содержит 10 постов опредленного автора."""
        response = self.guest_client.get(reverse(
            'posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(
            len(response.context['page_obj']), settings.NUMBER_POSTS)


class CashTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='username'
        )

    def setUp(self):
        self.guest_client = Client()

    def test_cache_index_page(self):
        """Проверка работы кеша."""
        cache1 = self.guest_client.get(reverse('posts:index')).content
        Post.objects.create(
            text='Cash text',
            author=self.user
        )
        cache2 = self.guest_client.get(reverse('posts:index')).content
        self.assertEqual(cache1, cache2)
        cache.clear()
        self.assertNotEqual(
            cache2, self.guest_client.get(reverse('posts:index')).content
        )


class FollowTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='TestAuthor'
        )
        self.user = User.objects.create_user(
            username='TestUser'
        )
        self.authorize_client = Client()
        self.authorize_client.force_login(self.user)

    def test_auth_user_can_follow(self):
        """Авторизованный пользователь может подписываться."""
        follow_count = Follow.objects.count()
        self.authorize_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.author.username}))
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(follow.author, self.author)
        self.assertEqual(follow.user, self.user)

    def test_auth_user_can_unfollow(self):
        """Авторизованный пользователь может отписываться."""
        follow_count = Follow.objects.count()
        Follow.objects.create(
            user=self.user,
            author=self.author
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.authorize_client.get(reverse(
            'posts:profile_unfollow', kwargs={
                'username': self.author.username}))
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_new_post_appear_in_follower_page(self):
        """Новая запись автора появляется в ленте тех, кто на него подписан."""
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.author
        )
        Follow.objects.create(
            author=self.author,
            user=self.user
        )
        response = self.authorize_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_new_post_dont_appear_in_follower_page(self):
        """Новая запись автора не появляется в ленте тех,
           кто на не него подписан."""
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.author
        )
        Follow.objects.create(
            author=self.author,
            user=self.user
        )
        self.second_user = User.objects.create_user(
            username='username',
        )
        self.authorize_client.force_login(self.second_user)
        response = self.authorize_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)
