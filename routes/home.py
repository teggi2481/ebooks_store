from flask import Blueprint, render_template, request
from models.ebook import EBook

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    if search_query:
        ebooks = EBook.query.filter(
            (EBook.title.ilike(f'%{search_query}%')) | 
            (EBook.author.ilike(f'%{search_query}%')) |
            (EBook.description.ilike(f'%{search_query}%'))
        ).all()
    else:
        ebooks = EBook.query.order_by(EBook.created_at.desc()).all()
    return render_template('index.html', ebooks=ebooks, search_query=search_query)
