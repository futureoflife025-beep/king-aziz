#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام ذكي لفهرس المكتبة
يبحث في قاعدة بيانات المكتبة ويجيب على الأسئلة
"""

import sqlite3
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اتصال قاعدة البيانات
DB_PATH = 'library.db'

def search_database(query, search_type='all', limit=10):
    """البحث في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    results = []
    
    try:
        if search_type == 'title':
            cursor.execute("""
                SELECT record_id, title, author, publisher, year, classification
                FROM books 
                WHERE title LIKE ? 
                LIMIT ?
            """, (f'%{query}%', limit))
        
        elif search_type == 'author':
            cursor.execute("""
                SELECT record_id, title, author, publisher, year, classification
                FROM books 
                WHERE author LIKE ? 
                LIMIT ?
            """, (f'%{query}%', limit))
        
        elif search_type == 'subject':
            cursor.execute("""
                SELECT record_id, title, author, publisher, year, subject
                FROM books 
                WHERE subject LIKE ? 
                LIMIT ?
            """, (f'%{query}%', limit))
        
        elif search_type == 'year':
            cursor.execute("""
                SELECT record_id, title, author, publisher, year, classification
                FROM books 
                WHERE year = ? 
                LIMIT ?
            """, (query, limit))
        
        else:  # بحث شامل
            cursor.execute("""
                SELECT record_id, title, author, publisher, year, classification
                FROM books 
                WHERE FULLTEXT_SEARCH LIKE ? 
                LIMIT ?
            """, (f'%{query}%', limit))
        
        results = cursor.fetchall()
    
    except Exception as e:
        logger.error(f"خطأ في البحث: {e}")
    
    finally:
        conn.close()
    
    return results

def format_result(book):
    """تنسيق نتيجة البحث"""
    record_id, title, author, publisher, year, extra = book
    
    text = f"📖 **{title}**\n\n"
    
    if author and author != 'nan':
        text += f"✍️ المؤلف: {author}\n"
    
    if publisher and publisher != 'nan':
        text += f"🏢 الناشر: {publisher}\n"
    
    if year and year != 'nan':
        text += f"📅 السنة: {year}\n"
    
    if extra and extra != 'nan':
        text += f"🔢 التصنيف: {extra}\n"
    
    text += f"🆔 رقم السجل: {record_id}\n"
    text += "─" * 30 + "\n"
    
    return text

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    welcome_text = """
🌟 **أهلاً بك في بوت مجمع الملك عبد العزير**

📚 لديّ قاعدة بيانات بـ **3,931 كتاب** جاهزة للبحث!

**الأوامر المتاحة:**

🔍 /search - بحث عام في جميع الحقول
✍️ /author - بحث بالمؤلف
📖 /title - بحث بالعنوان
📑 /subject - بحث بالموضوع
📅 /year - بحث بالسنة
📊 /stats - إحصائيات المكتبة
❓ /help - المساعدة

**أو اكتب أي سؤال مباشرة وسأبحث لك!**

مثال: "كتب ابن تيمية" أو "الفقه الحنبلي"
"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المساعدة"""
    help_text = """
📖 **كيفية استخدام البوت:**

**1️⃣ البحث البسيط:**
فقط اكتب ما تريد البحث عنه:
- "الفقه"
- "ابن القيم"
- "التفسير"

**2️⃣ البحث المتقدم:**
/search كلمة البحث
/author اسم المؤلف
/title عنوان الكتاب
/subject الموضوع
/year 1400

**3️⃣ أمثلة:**
- /author السيوطي
- /subject الحديث
- /year 1390
- /title صحيح

**💡 نصيحة:** يمكنك البحث بكلمة واحدة أو عدة كلمات
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإحصائيات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # إجمالي الكتب
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    
    # عدد المؤلفين
    cursor.execute("SELECT COUNT(DISTINCT author) FROM books WHERE author != 'nan'")
    total_authors = cursor.fetchone()[0]
    
    # أقدم كتاب
    cursor.execute("SELECT title, year FROM books WHERE year != 'nan' ORDER BY year LIMIT 1")
    oldest = cursor.fetchone()
    
    # أحدث كتاب
    cursor.execute("SELECT title, year FROM books WHERE year != 'nan' ORDER BY year DESC LIMIT 1")
    newest = cursor.fetchone()
    
    conn.close()
    
    stats_text = f"""
📊 **إحصائيات المكتبة:**

📚 إجمالي الكتب: **{total_books:,}**
✍️ عدد المؤلفين: **{total_authors:,}**

📅 أقدم كتاب: {oldest[0][:40]}... ({oldest[1]})
📅 أحدث كتاب: {newest[0][:40]}... ({newest[1]})

🔍 جاهز للبحث في أي وقت!
"""
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البحث العام"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة كلمة البحث\nمثال: /search الفقه")
        return
    
    query = ' '.join(context.args)
    await perform_search(update, query, 'all')

async def author_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث بالمؤلف"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة اسم المؤلف\nمثال: /author ابن تيمية")
        return
    
    query = ' '.join(context.args)
    await perform_search(update, query, 'author')

async def title_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث بالعنوان"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة عنوان الكتاب\nمثال: /title صحيح")
        return
    
    query = ' '.join(context.args)
    await perform_search(update, query, 'title')

async def subject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث بالموضوع"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة الموضوع\nمثال: /subject الحديث")
        return
    
    query = ' '.join(context.args)
    await perform_search(update, query, 'subject')

async def year_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث بالسنة"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة السنة\nمثال: /year 1400")
        return
    
    query = context.args[0]
    await perform_search(update, query, 'year')

async def perform_search(update: Update, query: str, search_type: str):
    """تنفيذ البحث وعرض النتائج"""
    await update.message.reply_text(f"🔍 جاري البحث عن: **{query}**...", parse_mode='Markdown')
    
    results = search_database(query, search_type, limit=10)
    
    if not results:
        await update.message.reply_text("😔 لم أجد أي نتائج. جرب كلمات بحث أخرى.")
        return
    
    # عرض النتائج
    response = f"✅ وجدت **{len(results)}** نتيجة:\n\n"
    
    for book in results:
        response += format_result(book)
        
        # تقسيم الرسائل إذا كانت طويلة
        if len(response) > 3500:
            await update.message.reply_text(response, parse_mode='Markdown')
            response = ""
    
    if response:
        await update.message.reply_text(response, parse_mode='Markdown')

import re

def detect_stats_question(query):
    """التعرف على أسئلة الإحصائيات"""
    # كلمات تدل على سؤال عن العدد أو الإحصائيات
    count_keywords = [
        'كم عدد', 'كم كتاب', 'عدد الكتب', 'إجمالي', 'اجمالي', 
        'كم مخطوطة', 'عدد المخطوطات', 'كم العناوين', 'عدد العناوين',
        'كم مؤلف', 'عدد المؤلفين', 'احصائيات', 'إحصائيات', 'إحصاء',
        'عطني احصائية', 'اعطني احصائية', 'أعطني إحصائية', 'عطني إحصائية',
        'احصائية', 'إحصائية', 'الاحصائيات', 'الإحصائيات',
        'عطني معلومات', 'اعطني معلومات', 'معلومات عامة',
        'كم لديك', 'كم عندك', 'ماذا لديك', 'ماذا عندك',
        'وش عندك', 'ايش عندك', 'شو عندك', 'كم فيه', 'كم موجود',
        'ملخص', 'نظرة عامة', 'تقرير', 'عدد السجلات'
    ]
    
    for keyword in count_keywords:
        if keyword in query:
            return True
    return False

def extract_record_id(query):
    """استخراج رقم السجل من النص"""
    # البحث عن أنماط مثل: رقم السجل 123، سجل 123، رقم 123، أو مجرد رقم
    patterns = [
        r'رقم\s*السجل\s*[:=]?\s*(\d+)',
        r'سجل\s*رقم\s*[:=]?\s*(\d+)',
        r'سجل\s*[:=]?\s*(\d+)',
        r'رقم\s*[:=]?\s*(\d+)',
        r'السجل\s*[:=]?\s*(\d+)',
        r'record\s*[:=]?\s*(\d+)',
        r'^(\d+)$',  # رقم فقط
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def search_by_record_id(record_id):
    """البحث برقم السجل"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT record_id, title, author, publisher, year, pages, classification, subject, isbn
        FROM books 
        WHERE record_id = ? OR record_id LIKE ?
    """, (record_id, f'%{record_id}%'))
    
    results = cursor.fetchall()
    conn.close()
    return results

def flexible_search(query, limit=15):
    """بحث مرن في جميع الحقول"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # تنظيف وتقسيم كلمات البحث
    words = query.strip().split()
    
    results = []
    
    # البحث في كل الحقول
    if len(words) == 1:
        word = words[0]
        cursor.execute("""
            SELECT DISTINCT record_id, title, author, publisher, year, classification
            FROM books 
            WHERE title LIKE ? 
               OR author LIKE ? 
               OR subject LIKE ?
               OR publisher LIKE ?
               OR classification LIKE ?
               OR record_id LIKE ?
               OR FULLTEXT_SEARCH LIKE ?
            LIMIT ?
        """, (f'%{word}%', f'%{word}%', f'%{word}%', f'%{word}%', f'%{word}%', f'%{word}%', f'%{word}%', limit))
    else:
        # بحث بعدة كلمات
        like_pattern = '%' + '%'.join(words) + '%'
        cursor.execute("""
            SELECT DISTINCT record_id, title, author, publisher, year, classification
            FROM books 
            WHERE title LIKE ? 
               OR author LIKE ? 
               OR FULLTEXT_SEARCH LIKE ?
               OR (title LIKE ? AND author LIKE ?)
            LIMIT ?
        """, (like_pattern, like_pattern, like_pattern, f'%{words[0]}%', f'%{words[-1]}%', limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def format_full_book_info(book):
    """تنسيق معلومات الكتاب الكاملة"""
    record_id, title, author, publisher, year, pages, classification, subject, isbn = book
    
    text = f"📖 **{title}**\n\n"
    text += f"🆔 رقم السجل: {record_id}\n"
    
    if author and author != 'nan':
        text += f"✍️ المؤلف: {author}\n"
    
    if publisher and publisher != 'nan':
        text += f"🏢 الناشر: {publisher}\n"
    
    if year and year != 'nan':
        text += f"📅 السنة: {year}\n"
    
    if pages and pages != 'nan':
        text += f"📄 الصفحات: {pages}\n"
    
    if classification and classification != 'nan':
        text += f"🔢 التصنيف: {classification}\n"
    
    if subject and subject != 'nan':
        subject_short = subject[:100] + "..." if len(str(subject)) > 100 else subject
        text += f"📑 الموضوع: {subject_short}\n"
    
    if isbn and isbn != 'nan':
        text += f"📕 ISBN: {isbn}\n"
    
    text += "─" * 30 + "\n"
    return text

def get_detailed_stats():
    """الحصول على إحصائيات تفصيلية من قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # إجمالي الكتب/العناوين
    cursor.execute("SELECT COUNT(*) FROM books")
    stats['total_books'] = cursor.fetchone()[0]
    
    # عدد المؤلفين الفريدين
    cursor.execute("SELECT COUNT(DISTINCT author) FROM books WHERE author != 'nan' AND author IS NOT NULL")
    stats['total_authors'] = cursor.fetchone()[0]
    
    # عدد الناشرين
    cursor.execute("SELECT COUNT(DISTINCT publisher) FROM books WHERE publisher != 'nan' AND publisher IS NOT NULL")
    stats['total_publishers'] = cursor.fetchone()[0]
    
    # عدد التصنيفات
    cursor.execute("SELECT COUNT(DISTINCT classification) FROM books WHERE classification != 'nan' AND classification IS NOT NULL")
    stats['total_classifications'] = cursor.fetchone()[0]
    
    # عدد الموضوعات
    cursor.execute("SELECT COUNT(DISTINCT subject) FROM books WHERE subject != 'nan' AND subject IS NOT NULL")
    stats['total_subjects'] = cursor.fetchone()[0]
    
    # أكثر 5 مؤلفين
    cursor.execute("""
        SELECT author, COUNT(*) as count 
        FROM books 
        WHERE author != 'nan' AND author IS NOT NULL
        GROUP BY author 
        ORDER BY count DESC 
        LIMIT 5
    """)
    stats['top_authors'] = cursor.fetchall()
    
    # أكثر 5 موضوعات
    cursor.execute("""
        SELECT subject, COUNT(*) as count 
        FROM books 
        WHERE subject != 'nan' AND subject IS NOT NULL
        GROUP BY subject 
        ORDER BY count DESC 
        LIMIT 5
    """)
    stats['top_subjects'] = cursor.fetchall()
    
    conn.close()
    return stats

async def handle_stats_question(update: Update, query: str):
    """الرد على أسئلة الإحصائيات"""
    stats = get_detailed_stats()
    
    response = f"""📊 **إحصائيات مجمع الملك عبد العزيز**

📚 **إجمالي العناوين/الكتب:** {stats['total_books']:,} كتاب
✍️ **عدد المؤلفين:** {stats['total_authors']:,} مؤلف
🏢 **عدد الناشرين:** {stats['total_publishers']:,} ناشر
📑 **عدد التصنيفات:** {stats['total_classifications']:,}
🏷️ **عدد الموضوعات:** {stats['total_subjects']:,}

"""
    
    if stats['top_authors']:
        response += "🔝 **أكثر المؤلفين كتباً:**\n"
        for i, (author, count) in enumerate(stats['top_authors'][:5], 1):
            if author and author != 'nan':
                author_short = author[:40] + "..." if len(author) > 40 else author
                response += f"   {i}. {author_short} ({count} كتاب)\n"
        response += "\n"
    
    response += "💡 للبحث عن كتاب معين، اكتب اسمه أو اسم المؤلف"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية العادية"""
    query = update.message.text.strip()
    
    if len(query) < 2:
        await update.message.reply_text("❌ الرجاء كتابة كلمة بحث أطول")
        return
    
    # التحقق إذا كان السؤال عن إحصائيات
    if detect_stats_question(query):
        await handle_stats_question(update, query)
        return
    
    # التحقق إذا كان البحث برقم السجل
    record_id = extract_record_id(query)
    if record_id:
        await update.message.reply_text(f"🔍 جاري البحث عن سجل رقم: **{record_id}**...", parse_mode='Markdown')
        results = search_by_record_id(record_id)
        
        if results:
            response = f"✅ تم العثور على **{len(results)}** سجل:\n\n"
            for book in results[:5]:
                response += format_full_book_info(book)
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"😔 لم أجد سجل برقم: {record_id}\n\n💡 تأكد من صحة الرقم أو جرب البحث بالعنوان")
        return
    
    # البحث المرن في جميع الحقول
    await update.message.reply_text(f"🔍 جاري البحث عن: **{query}**...", parse_mode='Markdown')
    
    results = flexible_search(query, limit=10)
    
    if not results:
        # محاولة بحث أكثر مرونة
        words = query.split()
        if len(words) > 1:
            # جرب البحث بكل كلمة على حدة
            for word in words:
                if len(word) > 2:
                    results = flexible_search(word, limit=10)
                    if results:
                        break
    
    if not results:
        suggestions = """😔 لم أجد نتائج مطابقة.

💡 **نصائح للبحث:**
• جرب كلمة واحدة بدلاً من جملة
• استخدم اسم المؤلف أو جزء من العنوان
• للبحث برقم السجل: اكتب "رقم السجل 123"
• لعرض الإحصائيات: اكتب "احصائيات" أو "كم عدد الكتب"

📝 **أمثلة:**
• ابن تيمية
• الفقه
• التفسير
• رقم السجل 511"""
        await update.message.reply_text(suggestions)
        return
    
    # عرض النتائج
    response = f"✅ وجدت **{len(results)}** نتيجة:\n\n"
    
    for book in results:
        response += format_result(book)
        
        if len(response) > 3500:
            await update.message.reply_text(response, parse_mode='Markdown')
            response = ""
    
    if response:
        await update.message.reply_text(response, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")
    
    if update and update.message:
        await update.message.reply_text("😔 عذراً، حدث خطأ. الرجاء المحاولة مرة أخرى.")

def main():
    """تشغيل البوت"""
    # التوكن من المتغيرات البيئية (آمن للرفع على GitHub)
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        print("❌ خطأ: لم يتم تعيين TELEGRAM_BOT_TOKEN")
        print("قم بتعيين المتغير البيئي أو أضف التوكن في Railway")
        return
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("author", author_command))
    application.add_handler(CommandHandler("title", title_command))
    application.add_handler(CommandHandler("subject", subject_command))
    application.add_handler(CommandHandler("year", year_command))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # تشغيل البوت
    print("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
