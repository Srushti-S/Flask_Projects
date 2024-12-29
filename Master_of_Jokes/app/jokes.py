from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from flask import flash, redirect, url_for, current_app
from .models import (
    get_db, 
    add_joke, 
    get_joke_balance, 
    is_joke_title_unique, 
    get_jokes_by_user_with_ratings, 
    get_joke_by_id, 
    update_joke_body, 
    get_non_authored_jokes, 
    mark_joke_as_taken, 
    delete_joke,
    add_joke_rating,
    get_average_rating,
    has_user_viewed_joke,
    mark_joke_as_viewed,
    has_user_taken_joke,
    get_all_jokes,
    get_all_users,
    get_user_role,
    set_user_role,
    get_moderator_count,
    update_user_role)



jokes_bp = Blueprint('jokes', __name__, url_prefix='/jokes')


# Role requirement decorator
def requires_role(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_role = session.get('role')
            if user_role != role:
                flash('Unauthorized access!', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@jokes_bp.route('/manage-balances', methods=['GET', 'POST'])
@requires_role('Moderator')
def manage_balances():
    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        new_balance = int(request.form.get('new_balance'))

        db = get_db()
        db.execute('UPDATE user SET joke_balance = ? WHERE id = ?', (new_balance, user_id))
        db.commit()

        flash('User balance updated successfully!', 'success')
        return redirect(url_for('jokes.manage_balances'))

    users = get_all_users()
    return render_template('moderate/manage_balances.html', users=users)


@jokes_bp.route('/manage-jokes', methods=['GET', 'POST'])
@requires_role('Moderator')
def manage_jokes():
    if request.method == 'POST':
        if 'delete' in request.form:
            joke_id = int(request.form.get('joke_id'))
            delete_joke(joke_id)
            flash('Joke deleted successfully.', 'success')
        elif 'edit' in request.form:
            joke_id = int(request.form.get('joke_id'))
            new_body = request.form.get('new_body')
            update_joke_body(joke_id, new_body, user_id=None)  
            flash('Joke updated successfully.', 'success')
        return redirect(url_for('jokes.manage_jokes'))

    jokes = get_all_jokes(None)  
    return render_template('moderate/manage_jokes.html', jokes=jokes)



@jokes_bp.route('/manage-roles', methods=['GET', 'POST'])
@requires_role('Moderator')
def manage_roles():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')

        if action == 'add_moderator':
            update_user_role(user_id, 'Moderator')
            flash('User promoted to Moderator successfully!', 'success')
        elif action == 'remove_moderator':
            if get_moderator_count() > 1: 
                update_user_role(user_id, 'User')
                flash('Moderator role removed successfully!', 'success')
            else:
                flash('Cannot remove the last Moderator!', 'danger')
        return redirect(url_for('jokes.manage_roles'))

    users = get_all_users()
    return render_template('moderate/manage_roles.html', users=users)




@jokes_bp.route('/toggle-debug', methods=['POST'])
@requires_role('Moderator')
def toggle_debug():
    current_app.config['DEBUG'] = not current_app.config['DEBUG']
    flash(f"Debug mode {'enabled' if current_app.config['DEBUG'] else 'disabled'}.", 'info')
    return redirect(url_for('jokes.manage_jokes'))


@jokes_bp.route('/my')
def my_jokes():
    if 'user_id' not in session:
        flash('You need to be logged in to view your jokes.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    joke_balance = get_joke_balance(user_id)  
    session['joke_balance'] = joke_balance  

    jokes = get_jokes_by_user_with_ratings(user_id)
    return render_template('jokes/my_jokes.html', jokes=jokes, joke_balance=joke_balance)



@jokes_bp.route('/<int:joke_id>/view', methods=['GET', 'POST'])
def view_joke(joke_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to view this page.', 'warning')
        return redirect(url_for('auth.login'))

    joke = get_joke_by_id(joke_id)
    if joke is None:
        flash('Joke not found or you do not have access to view it.', 'danger')
        return redirect(url_for('jokes.my_jokes'))

    if joke['author_id'] != user_id:
        if not has_user_viewed_joke(user_id, joke_id) and get_joke_balance(user_id) <= 0:
            flash('You need to add a joke before you can view others.', 'warning')
            return redirect(url_for('jokes.my_jokes'))
        elif not has_user_viewed_joke(user_id, joke_id):
            mark_joke_as_viewed(user_id, joke_id)  
            session['joke_balance'] = get_joke_balance(user_id)  

    average_rating = get_average_rating(joke_id)

    if request.method == 'POST':
        if 'update' in request.form and joke['author_id'] == user_id:
            new_body = request.form.get('body').strip()
            update_joke_body(joke_id, user_id, new_body)
            flash('Joke updated successfully!', 'success')
            return redirect(url_for('jokes.view_joke', joke_id=joke_id))

        elif 'delete' in request.form and joke['author_id'] == user_id:
            delete_joke(joke_id)
            flash('Joke deleted successfully!', 'success')
            return redirect(url_for('jokes.my_jokes'))

        elif 'rating' in request.form and joke['author_id'] != user_id:
            rating = int(request.form.get('rating'))
            add_joke_rating(joke_id, user_id, rating)
            flash('Rating submitted!', 'success')
            return redirect(url_for('jokes.view_joke', joke_id=joke_id))

    return render_template('jokes/view_joke.html', joke=joke, average_rating=average_rating, user_id=user_id)


@jokes_bp.route('/<int:joke_id>/edit', methods=['GET', 'POST'])
def edit_joke(joke_id):
    if 'user_id' not in session:
        flash('You need to be logged in to edit your jokes.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    joke = get_joke_by_id(joke_id, user_id)
    
    if joke is None:
        flash('Joke not found or you are not authorized to edit it.', 'danger')
        return redirect(url_for('jokes.my_jokes'))

    if request.method == 'POST':
        new_body = request.form.get('body').strip()
        update_joke_body(joke_id, user_id, new_body)
        flash('Joke updated successfully!', 'success')
        return redirect(url_for('jokes.my_jokes'))

    return render_template('jokes/edit_joke.html', joke=joke)


@jokes_bp.route('/leave', methods=['GET', 'POST'])
def leave_joke():
    if 'user_id' not in session:
        flash('You need to be logged in to leave a joke.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        title = request.form.get('title').strip()
        body = request.form.get('body').strip()

        if len(title.split()) > 10:
            flash('The joke title cannot exceed 10 words.', 'danger')
            return redirect(url_for('jokes.leave_joke'))

        if not is_joke_title_unique(title, user_id):
            flash('You have already used this joke title. Please choose another.', 'danger')
            return redirect(url_for('jokes.leave_joke'))

        if add_joke(title, body, user_id):
            session['joke_balance'] = get_joke_balance(user_id)  
            flash('Your joke was successfully added!', 'success')
            return redirect(url_for('jokes.my_jokes'))
        else:
            flash('An error occurred while adding your joke. Please try again.', 'danger')

    joke_balance = get_joke_balance(user_id)
    return render_template('jokes/leave_joke.html', joke_balance=joke_balance)


@jokes_bp.route('/take', methods=['GET', 'POST'])
def take_joke():
    if 'user_id' not in session:
        flash('You need to be logged in to take a joke.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    joke_balance = get_joke_balance(user_id)

    jokes = get_non_authored_jokes(user_id)

    if request.method == 'POST':
        joke_id = int(request.form.get('joke_id'))
        if has_user_taken_joke(user_id, joke_id):
            flash('You have already taken this joke.', 'warning')
        elif joke_balance <= 0:
            flash('You need to leave a joke before you can take one.', 'danger')
        else:
            mark_joke_as_taken(user_id, joke_id)
            session['joke_balance'] = get_joke_balance(user_id)
            flash('You have successfully taken the joke!', 'success')
            return redirect(url_for('jokes.my_jokes'))

    return render_template('jokes/take_joke.html', jokes=jokes, joke_balance=joke_balance)

