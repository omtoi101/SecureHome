from database import db, User


def create_user(username, password, is_admin=False):
    """Creates a new user and adds them to the database."""
    if User.query.filter_by(username=username).first():
        raise ValueError(f"User '{username}' already exists.")

    new_user = User(username=username, is_admin=is_admin)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()
    return new_user


def get_user_by_username(username):
    """Retrieves a user by their username."""
    return User.query.filter_by(username=username).first()


def get_user_by_id(user_id):
    """Retrieves a user by their ID."""
    return User.query.get(int(user_id))


def update_user_profile(
    user_id, new_username=None, new_password=None, is_admin=None
):
    """Updates a user's profile information."""
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User with ID '{user_id}' not found.")

    if new_username:
        # Check if the new username is already taken
        if (
            User.query.filter_by(username=new_username).first()
            and new_username != user.username
        ):
            raise ValueError(f"Username '{new_username}' is already taken.")
        user.username = new_username

    if new_password:
        user.set_password(new_password)

    if is_admin is not None:
        user.is_admin = is_admin

    db.session.commit()
    return user


def delete_user(user_id):
    """Deletes a user from the database."""
    user = get_user_by_id(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False


def get_all_users():
    """Returns a list of all users."""
    return User.query.all()
