import grp
from i18n import _


class GroupUtils:

    @classmethod
    def is_user_in_group(cls, username: str, group: str) -> bool:
        try:
            flatpak_group_info = grp.getgrnam(group)
            group_members = flatpak_group_info.gr_mem

            if username in group_members:
                return True
            else:
                return False

        except KeyError:
            print(_("Warning: the 'flatpak' group was not found on the system."))
            return False
        except Exception as e:
            print(_("An error occurred while checking the group: {error}").format(error=e))
            return False
