
from rest_framework import serializers

from .models import *
from .enums import *


class PlayerSerializer(serializers.Serializer):
    username = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    revealed_role = serializers.SerializerMethodField()
    secret_info = serializers.SerializerMethodField()

    def get_username(self, player):
        return player.user.username

    def get_full_name(self, player):
        return player.user.get_full_name()

    def get_status(self, player):
        return PlayerStatus.get_instance(player.status).name

    def get_revealed_role(self, player):
        return (
            Role.get_instance(player.role).name
            if player.role and player.status != PlayerStatus.ALIVE.code
            else None
        )

    def get_secret_info(self, player):
        if player.game.creator != self.context['user']:
            return None
        return {
            'role': _get_role_name(player.role),
            'old_role': _get_role_name(player.old_role),
            'older_role': _get_role_name(player.older_role),
            'actions_used': player.get_actions_used(),
            'doused': player.doused,
            'executioner_target': player.executioner_target,
        }


class UserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return user.get_full_name()


class GameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=GAME_NAME_MAX_LENGTH)
    created = serializers.DateField()
    creator = UserSerializer()
    players = serializers.ListField(
        child=PlayerSerializer(),
        source='get_players'
    )
    day_number = serializers.IntegerField()
    is_accepting = serializers.ReadOnlyField()
    user_has_joined = serializers.SerializerMethodField()

    def get_user_has_joined(self, game):
        return game.has_user_playing(self.context['user'])


def _get_role_name(role_code):
    return Role.get_instance(role_code).name if role_code else None