# posts/views.py
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Group, Post, User


def paginator_context(queryset, request):
    # Показывать по 10 записей на странице.
    paginator = Paginator(queryset, settings.NUMBER_POSTS)
    # Из URL извлекаем номер запрошенной страницы - это значение параметра page
    page_number = request.GET.get('page')
    # Получаем набор записей для страницы с запрошенным номером
    page_obj = paginator.get_page(page_number)
    return {
        'page_obj': page_obj
    }


def index(request):
    """Выводит шаблон главной страницы."""
    template = 'posts/index.html'
    context = paginator_context(Post.objects.all(), request)
    return render(request, template, context)


def group_posts(request, slug):
    """Выводит шаблон с группами постов."""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)

    context = {
        'group': group
    }

    context.update(paginator_context(group.posts.all(), request))
    return render(request, template, context)


def profile(request, username):
    """Выводит шаблон профа1ла пользователя"""
    template = 'posts/profile.html'
    # берем запись из модели юзер, где юзернейм соответсвует идентификатору,
    # который передается в параметре
    author = get_object_or_404(User, username=username)
    posts_count = author.posts.count()

    context = {
        'author': author,
        'posts_count': posts_count
    }

    context.update(paginator_context(author.posts.all(), request))
    return render(request, template, context)


def post_detail(request, post_id):
    """Выводит детальное описание поста и сам пост"""
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    posts_count = author.posts.count()
    form = CommentForm(request.POST or None)
    comments = post.comments.all()

    context = {
        'post': post,
        'posts_count': posts_count,
        'author': author,
        'form': form,
        'comments': comments
    }

    return render(request, template, context)


@login_required
def post_create(request):
    """Выводит шаблон создания постов."""
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, template, {'form': form})

    post = form.save(commit=False)
    post.author = request.user
    post.save()

    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    """Выводит шаблон редактирования поста."""
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)

    context = {
        'form': form,
        'post': post
    }

    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        # Получаем автора комментария
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)
