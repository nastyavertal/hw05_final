import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='username'
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post"""
        # Количество записей
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
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Достаем из базы последний созданный пост
        latest_post = Post.objects.first()
        # Проверяем, что создалась запись
        self.assertEqual(latest_post.text, form_data.get('text'))
        self.assertEqual(latest_post.group.id, self.group.id)
        self.assertEqual(latest_post.author, self.user)
        # Проверяем, что картинка появилась
        self.assertTrue(
            Post.objects.filter(
                image='posts/small.gif'
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый тестовый текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        # Проверяем, что количество постов не изменилось
        self.assertEqual(Post.objects.count(), posts_count)
        # Достаем из базы данных последний созданный пост
        latest_post = Post.objects.get(id=self.post.id)
        # Проверяем, что создалась запись
        self.assertEqual(latest_post.text, form_data.get('text'))
        self.assertEqual(latest_post.group.id, self.group.id)
        self.assertEqual(latest_post.author, self.user)

    def test_non_authorized_user_cant_create_a_post(self):
        """Проверка: неавторизованный
           пользователь не может создавать посты."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый тестовый текст',
            'group': self.group.id
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'users:login') + '?next=' + reverse('posts:post_create'))
        self.assertEqual(Post.objects.count(), posts_count)

    def test_non_authorize_client_comment(self):
        """Проверка: комментировать пост
           может только авторизованыый пользователь."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый текст комментария'
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)

    def test_succesful_comment_appear_in_page(self):
        """После успешной отправки комментарий появляется на странице поста."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый текст комментария'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
