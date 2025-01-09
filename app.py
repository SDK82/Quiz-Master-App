from flask import Flask, flash, render_template, request, redirect, session, url_for
from config import config
from models import db, User, Admin, Subject, Chapter, Quiz, Question, Quizresponse
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only



app = Flask(__name__)
app.config.from_object(config)


db.init_app(app)

with app.app_context():
    db.create_all()
    print("database created")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/dashboard/<username>")
def dashboard(username):
    user = User.query.filter_by(username=username).first()
    if user:
        # Fetch all subjects to display in the dropdown
        subjects = Subject.query.all()
        chapters = Chapter.query.all() 

        # Fetch completed quizzes for the user
        completed_quizzes = Quizresponse.query.filter_by(user_id=user.id).all()

        
        
        return render_template(
            "users_dashboard.html", 
            full_name=user.full_name, 
            subjects=subjects, 
            chapters=chapters, 
            completed_quizzes=completed_quizzes, 
            user=user
        )
    else:
        return "User not found", 404









@app.route('/subject/<int:subject_id>')
def subject_chapters(subject_id):
    # Get the chapters associated with this subject from the database
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    return render_template('chapters_page.html', subject=subject, chapters=chapters)

@app.route('/chapter/<int:chapter_id>/quizzes')
def chapter_quizzes(chapter_id):
    # Get the chapter and its related quizzes
    chapter = Chapter.query.get_or_404(chapter_id)
    quizzes = chapter.quizzes  # Get quizzes related to this chapter

    return render_template('quizzes_page.html', chapter=chapter, quizzes=quizzes)



@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    

    quiz = Quiz.query.get_or_404(quiz_id)  # Fetch the quiz using the provided ID
    questions = Question.query.filter_by(quiz_id=quiz_id).all()  # Fetch questions for the quiz

    # Parse the quiz date and time duration
    quiz_date = quiz.date_of_quiz  # Assuming quiz_date is in the format 'YYYY-MM-DD'
    time_duration_str = quiz.time_duration  # Assuming format "hh:mm"

    try:
        # Convert time_duration_str to timedelta
        hours, minutes = map(int, time_duration_str.split(':'))
        duration_timedelta = timedelta(hours=hours, minutes=minutes)
    except Exception as e:
        return f"Error parsing time_duration: {e}", 400

    # Assume the quiz starts at the beginning of the specified date (midnight)
    quiz_start_time = datetime.combine(quiz_date, datetime.min.time())
    quiz_end_time = quiz_start_time + duration_timedelta  # Calculate quiz end time

    # Get the current time
    current_time = datetime.now()

    # Log values for debugging
    print(f"Quiz Start Time: {quiz_start_time}")
    print(f"Quiz End Time: {quiz_end_time}")
    print(f"Current Time: {current_time}")

    # Calculate remaining time
    time_left = max(0, (quiz_end_time - current_time).total_seconds())  # Time left in seconds

    # Convert seconds to minutes for initial timer setup
    time_left_minutes = time_left // 60

    return render_template(
        'take_quiz.html',
        quiz=quiz,
        questions=questions,
        time_left=int(time_left_minutes)  # Pass remaining time in minutes to the template
    )



@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    # Fetch the quiz and user information
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session.get('user_id')  # Get the user id from the session
    
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if user is not authenticated
    
    total_scored = 0  # Initialize the score
    user_responses = {}  # Dictionary to store user responses
    
    for question in quiz.questions:
        selected_answer = request.form.get(f'question_{question.id}')
        user_responses[question.id] = selected_answer  # Save user's selected answer
        
        if selected_answer == question.correct_option:
            total_scored += question.marks  # Add the marks for the correct answer
    
    quiz_response = Quizresponse(
        quiz_id=quiz.id,
        user_id=user_id,
        total_scored=total_scored,
        user_responses=user_responses  # Save user's responses
    )
    
    db.session.add(quiz_response)
    db.session.commit()
    
    return redirect(url_for('quiz_result', quiz_response_id=quiz_response.id))

@app.route('/quiz_result/<int:quiz_response_id>')
def quiz_result(quiz_response_id):
    # Fetch the current quiz response, quiz, and user
    quiz_response = Quizresponse.query.get_or_404(quiz_response_id)
    quiz = Quiz.query.get_or_404(quiz_response.quiz_id)
    user = User.query.get_or_404(quiz_response.user_id)

    # Assuming user_responses is stored as JSON in the Quizresponse model
    user_responses = quiz_response.user_responses

    # Fetch the user's previous quiz scores and quiz names
    previous_scores = Quizresponse.query.filter_by(user_id=user.id).all()

    # Fetch all quizzes at once to avoid multiple queries
    quiz_names_dict = {quiz.id: quiz.name for quiz in Quiz.query.all()}

    # Convert previous_scores to a JSON-serializable list of dictionaries
    previous_scores_data = [{
        'quiz_name': quiz_names_dict.get(score.quiz_id, 'Unknown Quiz'),
        'score': score.total_scored
    } for score in previous_scores]

    # Calculate summary statistics
    total_scores = [score.total_scored for score in previous_scores]
    average_score = sum(total_scores) / len(total_scores) if total_scores else 0
    highest_score = max(total_scores) if total_scores else 0
    total_attempts = len(previous_scores)

    # Pass the necessary data to the template
    return render_template(
        'quiz_result.html', 
        quiz_response=quiz_response, 
        quiz=quiz, 
        user=user, 
        user_responses=user_responses,
        previous_scores=previous_scores_data,
        average_score=average_score,
        highest_score=highest_score,
        total_attempts=total_attempts
    )




# Route to search quizzes, subjects, and chapters
@app.route('/search', methods=['GET'])
def search_quizzes():
    query = request.args.get('query')
    # Search in subjects
    matching_subjects = Subject.query.filter(Subject.name.ilike(f'%{query}%')).all()
    # Search in chapters
    matching_chapters = Chapter.query.filter(Chapter.name.ilike(f'%{query}%')).all()
    # Search in quizzes
    matching_quizzes = Quiz.query.filter(Quiz.name.ilike(f'%{query}%')).all()
    
    return render_template('login.html', query=query)


@app.route('/user_summary_statistics/<int:user_id>')
def user_summary_statistics(user_id):
    # Fetch user and quiz responses
    user = User.query.get_or_404(user_id)
    quiz_responses = Quizresponse.query.filter_by(user_id=user.id).all()

    total_attempts = len(quiz_responses)
    scores = [response.total_scored for response in quiz_responses]

    # Fetch quiz names based on quiz_id
    labels = [Quiz.query.get(response.quiz_id).name for response in quiz_responses]

    # Display only the last 3 quizzes for comparison
    if total_attempts > 3:
        scores = scores[-3:]
        labels = labels[-3:]

    highest_score = max(scores, default=0)
    average_score = round(sum(scores) / total_attempts, 2) if total_attempts > 0 else 0

    summary_stats = {
        'total_attempts': total_attempts,
        'highest_score': highest_score,
        'average_score': average_score,
    }

    return render_template(
        'user_summary_statistics.html',
        user=user,
        summary_stats=summary_stats,
        labels=labels,
        scores=scores
    )
# ==============================================================================
#  Register and Login  page in home.html 
# ______________________________________________________________________________

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        full_name = request.form["full_name"]
        qualification = request.form["qualification"]
        dob = request.form["dob"]

        print(f"Received data: {username}, {full_name}, {qualification}, {dob}")  # Add print statement for debugging

        new_user = User(username=username, password=password, full_name=full_name, qualification=qualification, dob=dob)
        db.session.add(new_user)
        db.session.commit()
        print("User added successfully")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            # Store user_id in the session
            session['user_id'] = user.id
            return redirect(url_for("dashboard", username=user.username))
        else:
            return "Invalid credentials"
    return render_template("login.html")

# ===============================================================================

# Admin Login Page in admin_dashboard.html
# ________________________________________________________________________________

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # Query the Admin table for credentials
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session["admin_full_name"] = admin.full_name  # Store admin's full name in session
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials", 401
    return render_template("admin_login.html")
# =================================================================================

# Admins Dashboard Page in admin_dashboard.html
# _____________________________________________________________________________

@app.route("/admin-dashboard", methods=["GET", "POST"])
def admin_dashboard():
    # Ensure the admin is logged in
    if "admin_full_name" in session:
        full_name = session["admin_full_name"]
        
        search_query = request.args.get('search_query', '')
        
        # Search for users
        users = User.query.filter(User.username.like(f"%{search_query}%") | User.full_name.like(f"%{search_query}%")).all() if search_query else []
        
        # Search for subjects
        subjects = Subject.query.filter(Subject.name.like(f"%{search_query}%") | Subject.description.like(f"%{search_query}%")).all() if search_query else Subject.query.all()
        
        # Search for quizzes
        quizzes = Quiz.query.filter(Quiz.name.like(f"%{search_query}%")).all() if search_query else []
        
        return render_template("admins_dashboard.html", full_name=full_name, subjects=subjects, users=users, quizzes=quizzes)
    else:
        return redirect(url_for("admin_login"))

# ===============================================================================

# Admin Can see all users using "All Users" Button in admin_dashboard.html
# _______________________________________________________________________________

@app.route('/all_users')
def view_all_users():
    # Get the search query from the request arguments
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Filter users by full_name or username (case-insensitive search)
        users = User.query.filter(
            (User.full_name.ilike(f'%{search_query}%')) | 
            (User.username.ilike(f'%{search_query}%'))
        ).all()
    else:
        # Fetch all users if no search query is provided
        users = User.query.all()
    
    return render_template('view_all_users.html', users=users)

# =============================================================================

# /all_users : In this page a button under action column "View Quizzzes"
#  This route shows the users details when admin click on specific users Action 

# Route for user_quizzes.html

# _____________________________________________________________________________

@app.route('/user_quizzes/<int:user_id>')
def user_quizzes(user_id):
    # Fetch the user from the database
    user = User.query.get_or_404(user_id)
    
    # Fetch the quiz responses for this user
    quiz_responses = Quizresponse.query.filter_by(user_id=user.id).all()
    
    # Get the corresponding quizzes and results
    quizzes_with_results = []
    for quiz_response in quiz_responses:
        quiz = quiz_response.quiz
        
        # Check if quiz exists
        if quiz:
            quizzes_with_results.append({
                'quiz_name': quiz.name,
                'score': quiz_response.total_scored,
                'date': quiz_response.time_stamp_of_attempt.strftime('%d-%m-%Y %H:%M'),
            })
    
    # Pass the data to the template
    return render_template('user_quizzes.html', user=user, quizzes_with_results=quizzes_with_results)

# ==================================================================================
# This route contains "+ Create New Subject" button route from admins dashboard page

# button exists on admins_dashboard.html page
#  _____________________________________________________________________________

@app.route("/add-subject", methods=["GET", "POST"])
def add_subject():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description", "")

        new_subject = Subject(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()

        return redirect(url_for("admin_dashboard"))
    return render_template("add_subject.html")
# _________________________________________________________________________________

# Edit button in Existing Subject Cards for Admins Dashboard
# button exists on "admins_dashboard.html" page 
# It redirect "edit_subject.html" page 

# ___________________________________________________________________________________

@app.route("/edit-subject/<int:subject_id>", methods=["GET", "POST"])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if request.method == "POST":
        subject.name = request.form["name"]
        subject.description = request.form.get("description", "")
        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    return render_template("edit_subject.html", subject=subject)

# _________________________________________________________________________________

# Delete button in Existing Subject Cards for Admins Dashboard

# button exists on "admins_dashboard.html" page 
# It deletes existing cards from website and database also

# ___________________________________________________________________________________

@app.route("/delete-subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if subject:
        db.session.delete(subject)
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    else:
        return "Subject not found", 404

#  ===============================================================================

# "Add Chapter" button route 
# Button Route : @ add_chapters 

# route  exists on "admins_dashboard.html" page 
# Existing cards of subject 

# ___________________________________________________________________________________

    
@app.route('/add_chapters/<int:subject_id>', methods=['GET', 'POST'])
def add_chapters(subject_id):
    # Fetch the subject details
    subject = Subject.query.get(subject_id)
    if not subject:
        flash("Subject not found", "danger")
        return redirect(url_for('admin_dashboard'))

    # Fetch all chapters for the subject
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()

    if request.method == 'POST':
        # Get the chapter details from the form
        chapter_name = request.form.get('name')
        chapter_description = request.form.get('description')

        # Save the new chapter to the database
        new_chapter = Chapter(name=chapter_name, description=chapter_description, subject_id=subject.id)
        db.session.add(new_chapter)
        db.session.commit()

        flash("Chapter added successfully!", "success")
        return redirect(url_for('add_chapters', subject_id=subject.id))

    return render_template('add_chapters.html', subject=subject, chapters=chapters)

# ________________________________________________________________________________

# Route exists in Existing Chapter Section 
# button Edit
# Route : @ add_chapters.html  page 

#_________________________________________________________________________________

@app.route('/edit-chapter/<int:chapter_id>', methods=['GET', 'POST'])
def edit_chapter(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        flash("Chapter not found", "danger")
        return redirect(url_for('add_chapters', subject_id=chapter.subject_id))

    if request.method == 'POST':
        # Get the updated chapter details from the form
        chapter.name = request.form.get('name')
        chapter.description = request.form.get('description')

        # Commit the changes to the database
        db.session.commit()
        
        flash("Chapter updated successfully!", "success")
        return redirect(url_for('add_chapters', subject_id=chapter.subject_id))

    return render_template('edit_chapter.html', chapter=chapter)

# ________________________________________________________________________________

# Route exists in Existing Chapter Section 
# button Delete
# Route : @ add_chapters.html  page 

#_________________________________________________________________________________

@app.route('/delete-chapter/<int:chapter_id>', methods=['POST'])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    if chapter:
        db.session.delete(chapter)
        db.session.commit()
        flash("Chapter deleted successfully!", "success")
    else:
        flash("Chapter not found", "danger")
    return redirect(url_for('add_chapters', subject_id=chapter.subject_id))

# ==============================================================================

# This shows a form which creates quiz cards with details
# Create Quiz button in Existing Chapters cards 
# Route exists : add_chapters.html
# ______________________________________________________________________________

@app.route('/create_quiz/<int:chapter_id>', methods=['GET', 'POST'])
def create_quiz(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        flash("Chapter not found", "danger")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        quiz_name = request.form.get('quiz_name')
        date_of_quiz_str = request.form.get('date_of_quiz')
        time_duration = request.form.get('time_duration')
        total_marks = request.form.get('total_marks')

        try:
            date_of_quiz = datetime.strptime(date_of_quiz_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('create_quiz', chapter_id=chapter.id))

        new_quiz = Quiz(
            name=quiz_name,
            chapter_id=chapter.id,
            date_of_quiz=date_of_quiz,
            time_duration=time_duration,
            total_marks=total_marks
        )
        db.session.add(new_quiz)
        db.session.commit()

        flash("Quiz created successfully!", "success")
        return redirect(url_for('create_quiz', chapter_id=chapter.id))

    # Get the search query
    search_query = request.args.get('search_query', '').strip()
    
    if search_query:
        # Filter quizzes by name (case-insensitive)
        quizzes = Quiz.query.filter(
            Quiz.chapter_id == chapter.id,
            Quiz.name.ilike(f"%{search_query}%")
        ).all()
    else:
        quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()

    return render_template(
        'create_quiz.html', 
        chapter=chapter, 
        quizzes=quizzes, 
        search_query=search_query
    )
#______________________________________________________________________________

# This shows a form which edit quiz of existing cards of quizzes
# Edit Quiz button in Existing Quiz cards 
# Route exists : create_quiz.html
# ______________________________________________________________________________


@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash("Quiz not found", "danger")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        quiz.name = request.form.get('quiz_name')
        date_of_quiz_str = request.form.get('date_of_quiz')
        quiz.time_duration = request.form.get('time_duration')
        quiz.total_marks = request.form.get('total_marks')

        try:
            quiz.date_of_quiz = datetime.strptime(date_of_quiz_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('edit_quiz', quiz_id=quiz.id))

        db.session.commit()
        flash("Quiz updated successfully!", "success")
        return redirect(url_for('create_quiz', chapter_id=quiz.chapter_id))

    return render_template('edit_quiz.html', quiz=quiz)

#______________________________________________________________________________

# This shows delete quiz of existing cards of quizzes
# Delete Quiz button in Existing Quiz cards 
# Route exists : delete_quiz.html
# ______________________________________________________________________________

@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash("Quiz not found", "danger")
        return redirect(url_for('admin_dashboard'))

    chapter_id = quiz.chapter_id
    db.session.delete(quiz)
    db.session.commit()

    flash("Quiz deleted successfully!", "success")
    return redirect(url_for('create_quiz', chapter_id=chapter_id))

#______________________________________________________________________________

# This shows existing quiz cards have button : "Add Questions"
# Route exists : create_quiz.html
# ______________________________________________________________________________

# Add Questions Route
@app.route('/add_questions/<int:quiz_id>', methods=['GET', 'POST'])
def add_questions(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash("Quiz not found", "danger")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        question_statement = request.form.get('question_statement')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_option = request.form.get('correct_option')
        marks = request.form.get('marks')

        # Ensure all required fields are filled
        if not all([question_statement, option1, option2, correct_option, marks]):
            flash("Please fill in all required fields", "danger")
            return redirect(url_for('add_questions', quiz_id=quiz.id))

        try:
            marks = int(marks)
        except ValueError:
            flash("Marks must be a number", "danger")
            return redirect(url_for('add_questions', quiz_id=quiz.id))

        # Create a new question
        new_question = Question(
            quiz_id=quiz.id,
            question_statement=question_statement,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_option=correct_option,
            marks=marks
        )
        db.session.add(new_question)
        db.session.commit()

        flash("Question added successfully!", "success")
        return redirect(url_for('add_questions', quiz_id=quiz.id))

    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    return render_template('add_questions.html', quiz=quiz, questions=questions)

#______________________________________________________________________________

# This shows existing quiz cards have button : "Edit"
# Route exists : create_quiz.html
# ______________________________________________________________________________

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    # Retrieve the question by ID
    question = Question.query.get(question_id)
    if not question:
        flash("Question not found", "danger")
        return redirect(url_for('home'))  # Adjust redirection based on your app's flow

    if request.method == 'POST':
        # Retrieve form data
        question_statement = request.form.get('question_statement')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_option = request.form.get('correct_option')
        marks = request.form.get('marks')

        # Debugging: Ensure data is received
        app.logger.debug(f"Received Data: {request.form}")

        # Validate required fields
        if not all([question_statement, option1, option2, correct_option, marks]):
            flash("All required fields must be filled", "danger")
            return redirect(url_for('edit_question', question_id=question.id))

        # Validate marks as a float
        try:
            marks = float(marks)
        except ValueError:
            flash("Marks must be a valid number", "danger")
            return redirect(url_for('edit_question', question_id=question.id))

        # Update question details
        question.question_statement = question_statement
        question.option1 = option1
        question.option2 = option2
        question.option3 = option3
        question.option4 = option4
        question.correct_option = correct_option
        question.marks = marks

        try:
            # Commit changes to the database
            db.session.commit()
            flash("Question updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error committing to the database: {e}")
            flash("An error occurred while updating the question", "danger")

        # Redirect to the add questions page for the quiz
        return redirect(url_for('add_questions', quiz_id=question.quiz_id))

    # Render the edit form for GET requests
    return render_template('edit_question.html', question=question)



#______________________________________________________________________________

# This shows existing quiz cards have button : "Delete"
# Route exists : create_quiz.html
# ______________________________________________________________________________




# Route for deleting questions
@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("Question deleted successfully!", "success")
    return redirect(request.referrer)  # Redirect back to the same page

# ==============================================================================

#  "Summary Statistics" button in admin_dashboard.html
# Route for admin_summary_statistics.html

# ________________________________________________________________________________

@app.route("/admin-summary-statistics", methods=["GET"])
def admin_summary_statistics():
    if "admin_full_name" in session:
        full_name = session["admin_full_name"]
        
        # Subject-wise quiz count
        subject_quiz_count = db.session.query(
            Subject.name, db.func.count(Quiz.id)
        ).select_from(Subject).join(Chapter, Subject.id == Chapter.subject_id).join(Quiz, Chapter.id == Quiz.chapter_id).group_by(Subject.name).all()
        
        # Chapter-wise quiz count
        chapter_quiz_count = db.session.query(
            Chapter.name, db.func.count(Quiz.id)
        ).select_from(Chapter).join(Quiz, Chapter.id == Quiz.chapter_id).group_by(Chapter.name).all()
        
        # Quiz demand (based on quiz attempts)
        quiz_demand = db.session.query(
            Quiz.name, db.func.count(Quizresponse.id)
        ).select_from(Quiz).join(Quizresponse, Quiz.id == Quizresponse.quiz_id).group_by(Quiz.name).order_by(db.func.count(Quizresponse.id).desc()).all()

        # Prepare data for Chart.js
        subject_labels = [row[0] for row in subject_quiz_count]
        subject_data = [row[1] for row in subject_quiz_count]
        
        chapter_labels = [row[0] for row in chapter_quiz_count]
        chapter_data = [row[1] for row in chapter_quiz_count]
        
        quiz_labels = [row[0] for row in quiz_demand]
        quiz_data = [row[1] for row in quiz_demand]
        
        return render_template(
            "admin_summary_statistics.html",
            full_name=full_name,
            subject_labels=subject_labels,
            subject_data=subject_data,
            chapter_labels=chapter_labels,
            chapter_data=chapter_data,
            quiz_labels=quiz_labels,
            quiz_data=quiz_data
        )
    else:
        return redirect(url_for("admin_login"))
    
# ==============================================================================
# ADMIN
# ===============================================================================

if __name__ == "__main__":

    app.run(debug=True)



