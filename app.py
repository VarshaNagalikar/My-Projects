import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('BUGPILOT_SECRET_KEY', 'dev-only-change-this-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'bugpilot.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

ROLES = ['Tester', 'Developer', 'Project Manager']
# The 11-step status vocabulary shown in create, edit, search, and detail views.
STATUSES = ['New', 'Open', 'Assigned', 'In Progress', 'On Hold', 'Fixed', 'Ready for Testing', 'In Testing', 'Reopened', 'Verified', 'Closed']
PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
SEVERITIES = ['Minor', 'Major', 'Critical', 'Blocker']

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='Tester')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reported_bugs = db.relationship('Bug', foreign_keys='Bug.reporter_id', backref='reporter', lazy=True)
    assigned_bugs = db.relationship('Bug', foreign_keys='Bug.assignee_id', backref='assignee', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    steps_to_reproduce = db.Column(db.Text, default='')
    expected_result = db.Column(db.Text, default='')
    actual_result = db.Column(db.Text, default='')
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    severity = db.Column(db.String(20), nullable=False, default='Major')
    status = db.Column(db.String(30), nullable=False, default='New')
    environment = db.Column(db.String(160), default='')
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    comments = db.relationship('Comment', backref='bug', cascade='all, delete-orphan', lazy=True)
    history = db.relationship('StatusHistory', backref='bug', cascade='all, delete-orphan', lazy=True, order_by='StatusHistory.changed_at.desc()')

    @property
    def key(self):
        return f'BUG-{self.id:04d}'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bug_id = db.Column(db.Integer, db.ForeignKey('bug.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    author = db.relationship('User')

class StatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bug_id = db.Column(db.Integer, db.ForeignKey('bug.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_status = db.Column(db.String(30), nullable=False)
    new_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(255), default='')
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    bug_id = db.Column(db.Integer, db.ForeignKey('bug.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User')
    bug = db.relationship('Bug')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash('You do not have permission to perform that action.', 'danger')
                return redirect(url_for('dashboard'))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def notify(user_id, message, bug_id=None):
    if user_id:
        db.session.add(Notification(user_id=user_id, message=message, bug_id=bug_id))

def bug_or_404(bug_id):
    bug = db.session.get(Bug, bug_id)
    if bug is None:
        abort(404)
    return bug

def can_edit_bug(bug):
    return current_user.role == 'Project Manager' or current_user.id in [bug.reporter_id, bug.assignee_id] or current_user.role == 'Developer'

@app.context_processor
def inject_globals():
    unread_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return {'unread_count': unread_count, 'STATUSES': STATUSES, 'PRIORITIES': PRIORITIES, 'SEVERITIES': SEVERITIES}

@app.route('/')
def index():
    return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total = Bug.query.count()
    open_count = Bug.query.filter(Bug.status.notin_(['Verified', 'Closed'])).count()
    critical_count = Bug.query.filter((Bug.priority == 'Critical') | (Bug.severity.in_(['Critical', 'Blocker']))).filter(Bug.status != 'Closed').count()
    resolved_count = Bug.query.filter(Bug.status.in_(['Verified', 'Closed'])).count()
    recent = Bug.query.order_by(Bug.updated_at.desc()).limit(6).all()
    status_counts = {s: Bug.query.filter_by(status=s).count() for s in STATUSES}
    return render_template('dashboard.html', total=total, open_count=open_count, critical_count=critical_count,
                           resolved_count=resolved_count, recent=recent, status_counts=status_counts)

@app.route('/bugs')
@login_required
def bug_list():
    query = Bug.query
    search = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    assignee = request.args.get('assignee', '')
    if search:
        query = query.filter(db.or_(Bug.title.ilike(f'%{search}%'), Bug.description.ilike(f'%{search}%'), db.cast(Bug.id, db.String).ilike(f'%{search.replace("BUG-", "")}%')))
    if status in STATUSES:
        query = query.filter_by(status=status)
    if priority in PRIORITIES:
        query = query.filter_by(priority=priority)
    if assignee.isdigit():
        query = query.filter_by(assignee_id=int(assignee))
    bugs = query.order_by(Bug.updated_at.desc()).all()
    users = User.query.order_by(User.username).all()
    return render_template('bugs.html', bugs=bugs, users=users, filters={'q': search, 'status': status, 'priority': priority, 'assignee': assignee})

def validate_bug_form():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not title or not description:
        flash('Title and description are required.', 'danger')
        return None
    priority = request.form.get('priority', 'Medium')
    severity = request.form.get('severity', 'Major')
    if priority not in PRIORITIES or severity not in SEVERITIES:
        flash('Invalid priority or severity.', 'danger')
        return None
    status = request.form.get('status', 'New').strip()
    if status not in STATUSES:
        flash('Choose a valid bug lifecycle status.', 'danger')
        return None
    if current_user.role == 'Developer' and status in ['Verified', 'Closed']:
        flash('Developers cannot verify or close bugs; QA or the project manager must do that.', 'warning')
        return None
    if current_user.role == 'Tester' and status == 'Fixed':
        flash('Testers cannot mark a bug as Fixed.', 'warning')
        return None
    assignee_id = request.form.get('assignee_id', '').strip()
    assignee = db.session.get(User, int(assignee_id)) if assignee_id.isdigit() else None
    if assignee_id and not assignee:
        flash('Selected assignee does not exist.', 'danger')
        return None
    return {'title': title, 'description': description, 'steps_to_reproduce': request.form.get('steps_to_reproduce', '').strip(),
            'expected_result': request.form.get('expected_result', '').strip(), 'actual_result': request.form.get('actual_result', '').strip(),
            'priority': priority, 'severity': severity, 'environment': request.form.get('environment', '').strip(),
            'status': status, 'assignee': assignee}

@app.route('/bugs/new', methods=['GET', 'POST'])
@roles_required('Tester', 'Developer', 'Project Manager')
def bug_create():
    users = User.query.order_by(User.username).all()
    if request.method == 'POST':
        data = validate_bug_form()
        if data:
            bug = Bug(title=data['title'], description=data['description'], steps_to_reproduce=data['steps_to_reproduce'],
                      expected_result=data['expected_result'], actual_result=data['actual_result'], priority=data['priority'],
                      severity=data['severity'], environment=data['environment'], reporter_id=current_user.id,
                      assignee_id=data['assignee'].id if data['assignee'] else None, status=data['status'])
            db.session.add(bug)
            db.session.flush()
            db.session.add(StatusHistory(bug_id=bug.id, user_id=current_user.id, old_status='—', new_status=bug.status, note='Bug created'))
            if data['assignee']:
                notify(data['assignee'].id, f'{bug.key} was assigned to you: {bug.title}', bug.id)
            db.session.commit()
            flash(f'{bug.key} created successfully.', 'success')
            return redirect(url_for('bug_detail', bug_id=bug.id))
    return render_template('bug_form.html', bug=None, users=users)

@app.route('/bugs/<int:bug_id>')
@login_required
def bug_detail(bug_id):
    bug = bug_or_404(bug_id)
    return render_template('bug_detail.html', bug=bug, users=User.query.order_by(User.username).all())

@app.route('/bugs/<int:bug_id>/edit', methods=['GET', 'POST'])
@login_required
def bug_edit(bug_id):
    bug = bug_or_404(bug_id)
    if not can_edit_bug(bug):
        abort(403)
    users = User.query.order_by(User.username).all()
    if request.method == 'POST':
        data = validate_bug_form()
        if data:
            previous_assignee = bug.assignee_id
            previous_status = bug.status
            for key in ['title', 'description', 'steps_to_reproduce', 'expected_result', 'actual_result', 'priority', 'severity', 'environment']:
                setattr(bug, key, data[key])
            bug.assignee_id = data['assignee'].id if data['assignee'] else None
            bug.status = data['status']
            if bug.assignee_id and bug.assignee_id != previous_assignee:
                notify(bug.assignee_id, f'{bug.key} was assigned to you: {bug.title}', bug.id)
            if previous_status != bug.status:
                db.session.add(StatusHistory(bug_id=bug.id, user_id=current_user.id, old_status=previous_status, new_status=bug.status, note='Status changed while editing issue'))
                for uid in {bug.reporter_id, bug.assignee_id}:
                    if uid and uid != current_user.id:
                        notify(uid, f'{bug.key} status changed: {previous_status} → {bug.status}', bug.id)
            db.session.commit()
            flash(f'{bug.key} updated.', 'success')
            return redirect(url_for('bug_detail', bug_id=bug.id))
    return render_template('bug_form.html', bug=bug, users=users)

@app.route('/bugs/<int:bug_id>/status', methods=['POST'])
@login_required
def bug_status(bug_id):
    bug = bug_or_404(bug_id)
    new_status = request.form.get('status', '')
    if new_status not in STATUSES:
        flash('Invalid status.', 'danger')
        return redirect(url_for('bug_detail', bug_id=bug.id))
    if current_user.role == 'Developer' and new_status in ['Verified', 'Closed']:
        flash('Developers cannot verify or close bugs; QA or the project manager must do that.', 'warning')
        return redirect(url_for('bug_detail', bug_id=bug.id))
    if current_user.role == 'Tester' and new_status in ['Fixed']:
        flash('Testers cannot mark a bug as Fixed.', 'warning')
        return redirect(url_for('bug_detail', bug_id=bug.id))
    old_status = bug.status
    if old_status != new_status:
        bug.status = new_status
        db.session.add(StatusHistory(bug_id=bug.id, user_id=current_user.id, old_status=old_status, new_status=new_status))
        recipients = {bug.reporter_id, bug.assignee_id}
        for uid in recipients:
            if uid and uid != current_user.id:
                notify(uid, f'{bug.key} status changed: {old_status} → {new_status}', bug.id)
        db.session.commit()
        flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('bug_detail', bug_id=bug.id))

@app.route('/bugs/<int:bug_id>/comments', methods=['POST'])
@login_required
def add_comment(bug_id):
    bug = bug_or_404(bug_id)
    body = request.form.get('body', '').strip()
    if body:
        db.session.add(Comment(bug_id=bug.id, user_id=current_user.id, body=body[:4000]))
        for uid in {bug.reporter_id, bug.assignee_id}:
            if uid and uid != current_user.id:
                notify(uid, f'New comment on {bug.key}', bug.id)
        db.session.commit()
        flash('Comment added.', 'success')
    return redirect(url_for('bug_detail', bug_id=bug.id) + '#comments')

@app.route('/bugs/<int:bug_id>/delete', methods=['POST'])
@roles_required('Project Manager')
def bug_delete(bug_id):
    bug = bug_or_404(bug_id)
    db.session.delete(bug)
    db.session.commit()
    flash('Bug deleted.', 'success')
    return redirect(url_for('bug_list'))

@app.route('/notifications')
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    for item in items:
        item.read = True
    db.session.commit()
    return render_template('notifications.html', items=items)

@app.route('/users')
@roles_required('Project Manager')
def users_page():
    users = User.query.order_by(User.role, User.username).all()
    return render_template('users.html', users=users)

@app.errorhandler(403)
def forbidden(_error):
    return render_template('error.html', code=403, message='You do not have permission to access this page.'), 403

@app.errorhandler(404)
def not_found(_error):
    return render_template('error.html', code=404, message='The page or bug you requested was not found.'), 404

@app.cli.command('seed')
def seed_command():
    """Create demo users and sample bug reports."""
    db.create_all()
    if User.query.first():
        print('Database already has users; seed skipped.')
        return
    accounts = [
        ('tester', 'tester@bugpilot.local', 'Tester', 'Tester123!'),
        ('developer', 'developer@bugpilot.local', 'Developer', 'Developer123!'),
        ('manager', 'manager@bugpilot.local', 'Project Manager', 'Manager123!'),
    ]
    users = []
    for username, email, role, password in accounts:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        users.append(user)
    db.session.flush()
    examples = [
        ('Login button does not respond on first click', 'The login button sometimes ignores the first click on the sign-in page.', 'Open login page; enter valid credentials; click Sign in once.', 'User should be signed in.', 'No response until the second click.', 'High', 'Major', 'In Progress', 'Chrome / Windows 11', users[0].id, users[1].id),
        ('Profile page shows incorrect timezone', 'The activity timestamp is displayed three hours ahead of the configured timezone.', 'Open Profile → Activity after changing timezone.', 'Timestamps should use the configured timezone.', 'Timestamps are three hours ahead.', 'Medium', 'Minor', 'New', 'Firefox / Ubuntu', users[0].id, None),
        ('Checkout crashes when cart is empty', 'Submitting checkout with an empty cart results in a server error.', 'Remove all cart items and click Checkout.', 'Show an empty-cart validation message.', 'A 500 error page is shown.', 'Critical', 'Blocker', 'Assigned', 'Edge / Windows 11', users[0].id, users[1].id),
        ('Password reset confirmation email delayed', 'Password reset emails take more than five minutes to arrive in the test environment.', 'Request a password reset using a valid test account.', 'Email should arrive within one minute.', 'Email arrives after five minutes.', 'Low', 'Minor', 'Fixed', 'Staging environment', users[0].id, users[1].id),
        ('Search filter resets after page refresh', 'The status filter is lost when the issue list page is refreshed.', 'Filter bugs by In Progress and refresh the page.', 'The selected filter should remain applied.', 'All statuses appear again.', 'Medium', 'Major', 'Ready for Testing', 'Chrome / macOS', users[0].id, users[1].id),
    ]
    for row in examples:
        bug = Bug(title=row[0], description=row[1], steps_to_reproduce=row[2], expected_result=row[3], actual_result=row[4], priority=row[5], severity=row[6], status=row[7], environment=row[8], reporter_id=row[9], assignee_id=row[10])
        db.session.add(bug)
        db.session.flush()
        db.session.add(StatusHistory(bug_id=bug.id, user_id=users[0].id, old_status='—', new_status=bug.status, note='Sample bug seeded'))
    db.session.commit()
    print('Demo users and sample bugs created.')
    print('tester / Tester123! | developer / Developer123! | manager / Manager123!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.environ.get('FLASK_DEBUG', '1') == '1')
