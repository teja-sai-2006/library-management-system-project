#!/usr/bin/env python3
"""Populate library with 30+ demo books"""

from database_setup import DatabaseManager

def populate_library():
    db = DatabaseManager()
    
    print("🗑️  Clearing existing books data...")
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM book_issues')
        cursor.execute('DELETE FROM books')
        cursor.execute('DELETE FROM book_categories')
        conn.commit()
        conn.close()
        print("✅ Cleared existing data\n")
    except:
        pass
    
    print("📚 Adding categories...")
    
    categories = [
        ("Fiction", "Novels, short stories, and fictional works"),
        ("Non-Fiction", "Biographies, history, and factual books"),
        ("Science", "Physics, chemistry, biology, and scientific research"),
        ("Technology", "Computer science, engineering, and technical books"),
        ("Philosophy", "Philosophy, ethics, and thought-provoking books"),
        ("Business", "Management, entrepreneurship, and business books")
    ]
    
    cat_ids = {}
    for name, desc in categories:
        cat_id = db.add_category(name, desc)
        cat_ids[name] = cat_id
        print(f"  ✓ {name}")
    
    print(f"\n📖 Adding 31 books...\n")
    
    books = [
        # Fiction (10 books)
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "isbn": "978-0-06-112008-4", "category_id": cat_ids["Fiction"], "shelf_number": "A1", "rack_number": "1", "total_copies": 5, "publisher": "J.B. Lippincott & Co.", "publication_year": 1960, "cover_image_url": "https://covers.openlibrary.org/b/id/8228691-L.jpg", "description": "Classic novel of a lawyer in the Deep South defending a black man."},
        {"title": "1984", "author": "George Orwell", "isbn": "978-0-452-28423-4", "category_id": cat_ids["Fiction"], "shelf_number": "A1", "rack_number": "2", "total_copies": 4, "publisher": "Secker & Warburg", "publication_year": 1949, "cover_image_url": "https://covers.openlibrary.org/b/id/7222246-L.jpg", "description": "Dystopian novel about totalitarianism."},
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "978-0-7432-7356-5", "category_id": cat_ids["Fiction"], "shelf_number": "A1", "rack_number": "3", "total_copies": 6, "publisher": "Charles Scribner's Sons", "publication_year": 1925, "cover_image_url": "https://covers.openlibrary.org/b/id/7222339-L.jpg", "description": "The American Dream in the Jazz Age."},
        {"title": "Pride and Prejudice", "author": "Jane Austen", "isbn": "978-0-14-143951-8", "category_id": cat_ids["Fiction"], "shelf_number": "A1", "rack_number": "4", "total_copies": 4, "publisher": "Penguin Classics", "publication_year": 1813, "cover_image_url": "https://covers.openlibrary.org/b/id/8225512-L.jpg", "description": "Romantic novel following Elizabeth Bennet."},
        {"title": "Harry Potter and the Sorcerer's Stone", "author": "J.K. Rowling", "isbn": "978-0-439-70818-8", "category_id": cat_ids["Fiction"], "shelf_number": "A2", "rack_number": "1", "total_copies": 8, "publisher": "Scholastic", "publication_year": 1997, "cover_image_url": "https://covers.openlibrary.org/b/id/10521270-L.jpg", "description": "Harry's first year at Hogwarts."},
        {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "isbn": "978-0-316-76948-0", "category_id": cat_ids["Fiction"], "shelf_number": "A2", "rack_number": "2", "total_copies": 3, "publisher": "Little, Brown", "publication_year": 1951, "cover_image_url": "https://covers.openlibrary.org/b/id/8228232-L.jpg", "description": "Holden Caulfield's experiences in NYC."},
        {"title": "Lord of the Flies", "author": "William Golding", "isbn": "978-0-399-50148-7", "category_id": cat_ids["Fiction"], "shelf_number": "A2", "rack_number": "3", "total_copies": 5, "publisher": "Faber and Faber", "publication_year": 1954, "cover_image_url": "https://covers.openlibrary.org/b/id/8228457-L.jpg", "description": "Boys stranded on an island."},
        {"title": "The Hobbit", "author": "J.R.R. Tolkien", "isbn": "978-0-547-92822-7", "category_id": cat_ids["Fiction"], "shelf_number": "A3", "rack_number": "1", "total_copies": 6, "publisher": "Houghton Mifflin", "publication_year": 1937, "cover_image_url": "https://covers.openlibrary.org/b/id/8593810-L.jpg", "description": "Bilbo's journey to the Lonely Mountain."},
        {"title": "Brave New World", "author": "Aldous Huxley", "isbn": "978-0-06-085052-4", "category_id": cat_ids["Fiction"], "shelf_number": "A3", "rack_number": "2", "total_copies": 4, "publisher": "Harper Perennial", "publication_year": 1932, "cover_image_url": "https://covers.openlibrary.org/b/id/8228147-L.jpg", "description": "Dystopian novel about a futuristic World State."},
        {"title": "Animal Farm", "author": "George Orwell", "isbn": "978-0-452-28424-1", "category_id": cat_ids["Fiction"], "shelf_number": "A3", "rack_number": "3", "total_copies": 5, "publisher": "Secker & Warburg", "publication_year": 1945, "cover_image_url": "https://covers.openlibrary.org/b/id/8228042-L.jpg", "description": "Allegorical novella about totalitarianism."},
        
        # Non-Fiction (6 books)
        {"title": "Sapiens", "author": "Yuval Noah Harari", "isbn": "978-0-06-231609-7", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B2", "rack_number": "1", "total_copies": 5, "publisher": "Harper", "publication_year": 2011, "cover_image_url": "https://covers.openlibrary.org/b/id/8739161-L.jpg", "description": "History of humankind from Stone Age to modern age."},
        {"title": "Educated", "author": "Tara Westover", "isbn": "978-0-399-59050-4", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B2", "rack_number": "2", "total_copies": 4, "publisher": "Random House", "publication_year": 2018, "cover_image_url": "https://covers.openlibrary.org/b/id/8531910-L.jpg", "description": "Memoir about education and family."},
        {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "isbn": "978-0-374-53355-7", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B2", "rack_number": "3", "total_copies": 4, "publisher": "Farrar, Straus", "publication_year": 2011, "cover_image_url": "https://covers.openlibrary.org/b/id/7884823-L.jpg", "description": "Two systems that drive how we think."},
        {"title": "Atomic Habits", "author": "James Clear", "isbn": "978-0-735-21129-2", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B3", "rack_number": "1", "total_copies": 7, "publisher": "Avery", "publication_year": 2018, "cover_image_url": "https://covers.openlibrary.org/b/id/8633909-L.jpg", "description": "Build good habits and break bad ones."},
        {"title": "Outliers", "author": "Malcolm Gladwell", "isbn": "978-0-316-01792-3", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B3", "rack_number": "2", "total_copies": 5, "publisher": "Little, Brown", "publication_year": 2008, "cover_image_url": "https://covers.openlibrary.org/b/id/6999920-L.jpg", "description": "The story of success."},
        {"title": "The Immortal Life of Henrietta Lacks", "author": "Rebecca Skloot", "isbn": "978-1-400-05217-2", "category_id": cat_ids["Non-Fiction"], "shelf_number": "B3", "rack_number": "3", "total_copies": 3, "publisher": "Crown", "publication_year": 2010, "cover_image_url": "https://covers.openlibrary.org/b/id/8231487-L.jpg", "description": "Story of HeLa cells."},
        
        # Science (5 books)
        {"title": "A Brief History of Time", "author": "Stephen Hawking", "isbn": "978-0-553-38016-3", "category_id": cat_ids["Science"], "shelf_number": "C3", "rack_number": "1", "total_copies": 4, "publisher": "Bantam Books", "publication_year": 1988, "cover_image_url": "https://covers.openlibrary.org/b/id/8227974-L.jpg", "description": "How did the universe begin?"},
        {"title": "The Selfish Gene", "author": "Richard Dawkins", "isbn": "978-0-19-929114-4", "category_id": cat_ids["Science"], "shelf_number": "C3", "rack_number": "2", "total_copies": 3, "publisher": "Oxford University", "publication_year": 1976, "cover_image_url": "https://covers.openlibrary.org/b/id/8228133-L.jpg", "description": "Gene-centered view of evolution."},
        {"title": "Cosmos", "author": "Carl Sagan", "isbn": "978-0-375-50832-5", "category_id": cat_ids["Science"], "shelf_number": "C3", "rack_number": "3", "total_copies": 4, "publisher": "Random House", "publication_year": 1980, "cover_image_url": "https://covers.openlibrary.org/b/id/8228295-L.jpg", "description": "Journey through the universe."},
        {"title": "The Gene", "author": "Siddhartha Mukherjee", "isbn": "978-1-476-73337-7", "category_id": cat_ids["Science"], "shelf_number": "C4", "rack_number": "1", "total_copies": 4, "publisher": "Scribner", "publication_year": 2016, "cover_image_url": "https://covers.openlibrary.org/b/id/8451184-L.jpg", "description": "Biography of the gene."},
        {"title": "Astrophysics for People in a Hurry", "author": "Neil deGrasse Tyson", "isbn": "978-0-393-60939-4", "category_id": cat_ids["Science"], "shelf_number": "C4", "rack_number": "2", "total_copies": 6, "publisher": "W. W. Norton", "publication_year": 2017, "cover_image_url": "https://covers.openlibrary.org/b/id/8451822-L.jpg", "description": "Quick overview of the universe."},
        
        # Technology (5 books)
        {"title": "Clean Code", "author": "Robert C. Martin", "isbn": "978-0-13-235088-4", "category_id": cat_ids["Technology"], "shelf_number": "D4", "rack_number": "1", "total_copies": 5, "publisher": "Prentice Hall", "publication_year": 2008, "cover_image_url": "https://covers.openlibrary.org/b/id/6999229-L.jpg", "description": "Agile software craftsmanship."},
        {"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "isbn": "978-0-13-595705-9", "category_id": cat_ids["Technology"], "shelf_number": "D4", "rack_number": "2", "total_copies": 4, "publisher": "Addison-Wesley", "publication_year": 1999, "cover_image_url": "https://covers.openlibrary.org/b/id/7893541-L.jpg", "description": "Journey to mastery."},
        {"title": "Cracking the Coding Interview", "author": "Gayle McDowell", "isbn": "978-0-984-78215-0", "category_id": cat_ids["Technology"], "shelf_number": "D5", "rack_number": "1", "total_copies": 6, "publisher": "CareerCup", "publication_year": 2015, "cover_image_url": "https://covers.openlibrary.org/b/id/8231156-L.jpg", "description": "189 programming questions."},
        {"title": "Design Patterns", "author": "Gang of Four", "isbn": "978-0-201-63361-0", "category_id": cat_ids["Technology"], "shelf_number": "D5", "rack_number": "2", "total_copies": 3, "publisher": "Addison-Wesley", "publication_year": 1994, "cover_image_url": "https://covers.openlibrary.org/b/id/7893269-L.jpg", "description": "Reusable object-oriented software."},
        {"title": "Code Complete", "author": "Steve McConnell", "isbn": "978-0-735-61967-8", "category_id": cat_ids["Technology"], "shelf_number": "D5", "rack_number": "3", "total_copies": 3, "publisher": "Microsoft Press", "publication_year": 2004, "cover_image_url": "https://covers.openlibrary.org/b/id/6999548-L.jpg", "description": "Software construction handbook."},
        
        # Philosophy (3 books)
        {"title": "Meditations", "author": "Marcus Aurelius", "isbn": "978-0-14-044933-1", "category_id": cat_ids["Philosophy"], "shelf_number": "E5", "rack_number": "1", "total_copies": 4, "publisher": "Penguin Classics", "publication_year": 180, "cover_image_url": "https://covers.openlibrary.org/b/id/8228654-L.jpg", "description": "Stoic philosophy notes."},
        {"title": "The Republic", "author": "Plato", "isbn": "978-0-14-044914-0", "category_id": cat_ids["Philosophy"], "shelf_number": "E5", "rack_number": "2", "total_copies": 3, "publisher": "Penguin Classics", "publication_year": -380, "cover_image_url": "https://covers.openlibrary.org/b/id/8228789-L.jpg", "description": "Dialogue on justice."},
        {"title": "Man's Search for Meaning", "author": "Viktor Frankl", "isbn": "978-0-8070-1427-1", "category_id": cat_ids["Philosophy"], "shelf_number": "E5", "rack_number": "3", "total_copies": 5, "publisher": "Beacon Press", "publication_year": 1946, "cover_image_url": "https://covers.openlibrary.org/b/id/8228623-L.jpg", "description": "Life in concentration camps."},
        
        # Business (2 books)
        {"title": "The Lean Startup", "author": "Eric Ries", "isbn": "978-0-307-88789-4", "category_id": cat_ids["Business"], "shelf_number": "F6", "rack_number": "1", "total_copies": 5, "publisher": "Crown Business", "publication_year": 2011, "cover_image_url": "https://covers.openlibrary.org/b/id/7893912-L.jpg", "description": "Continuous innovation."},
        {"title": "Good to Great", "author": "Jim Collins", "isbn": "978-0-066-62099-2", "category_id": cat_ids["Business"], "shelf_number": "F6", "rack_number": "2", "total_copies": 5, "publisher": "HarperBusiness", "publication_year": 2001, "cover_image_url": "https://covers.openlibrary.org/b/id/8228367-L.jpg", "description": "Companies that make the leap."}
    ]
    
    count = 0
    for book_data in books:
        try:
            book_id = db.add_book(**book_data)
            count += 1
            print(f"  {count}. {book_data['title']:<45} by {book_data['author']}")
        except Exception as e:
            print(f"  ❌ {book_data['title']}: {e}")
    
    print(f"\n{'='*70}")
    print(f"✅ Library populated successfully!")
    print(f"{'='*70}")
    print(f"\n📊 Summary:")
    print(f"  📚 Categories: {len(categories)}")
    print(f"  📖 Books: {count}")
    print(f"  📦 Total copies: {sum(b['total_copies'] for b in books)}")
    print(f"\n🌐 Access:")
    print(f"  👑 Admin Panel: http://localhost:5000/admin.html")
    print(f"  📚 Browse Books: http://localhost:5000/books_tracking.html")
    print(f"\n💡 Use +/- buttons in admin panel to issue/return books!")

if __name__ == '__main__':
    populate_library()
