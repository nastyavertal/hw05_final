from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


# наследуется класс UserCreationForm:
class CreationForm(UserCreationForm):
    # наследуется класс Meta, вложенный в класс UserCreationForm:
    class Meta(UserCreationForm.Meta):
        # на основе какой модели создается класс
        model = User
        # какие поля должны быть видны в форме
        fields = ('first_name', 'last_name', 'username', 'email')
