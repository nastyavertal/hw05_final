# posts/tests/test_urls.py
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст'
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_pages_are_available_to_everyone(self):
        """Страницы доступны любому пользователю."""
        urls_pages_address = {
            reverse('posts:index'): HTTPStatus.OK,
            reverse('posts:group_list', kwargs={'slug': self.group.slug}): HTTPStatus.OK,
            reverse('posts:profile', kwargs={'username': self.user}): HTTPStatus.OK,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}): HTTPStatus.OK
        }
        for urls, status in urls_pages_address.items():
            with self.subTest(urls=urls):
                response = self.guest_client.get(urls)
                self.assertEqual(response.status_code, status)

    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/post_id/edit/ доступна ТОЛЬКО АВТОРУ поста."""
        if self.post.author == self.user:
            response = self.authorized_client.get(
                f'/posts/{self.post.id}/edit/'
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url_exists_at_desired_location(self):
        """Страница по адресу /create/
           доступна только авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        response = self.guest_client.get('/unexisting/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_name = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html'
        }
        for address, template in templates_url_name.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
