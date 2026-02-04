#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تليجرام ذكي بالـ AI - نسخة متقدمة
يستخدم Claude API للإجابة الذكية على الأسئلة
"""

import sqlite3
import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعدادات
DB_PATH = 'library.db'
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # اختياري - للنسخة الذكية

def get_relevant_books(query, limit=15):
    """البحث في قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT record_id, title, author, publisher, year, classification, subject, pages
        FROM books 
        WHERE FULLTEXT_SEARCH LIKE ? 
        LIMIT ?
    """, (f'%{query}%', limit))
    
    results = cursor.fetchall()
    conn.close()
    
    # تحويل النتائج إلى قاموس
    books = []
    for row in results:
        books.append({
            'record_id': row[0],
            'title': row[1],
            'author': row[2],
            'publisher': row[3],
            'year': row[4],
            'classification': row[5],
            'subject': row[6],
            'pages': row[7]
        })
    
    return books

def get_stats():
    """الحصول على إحصائيات المكتبة"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM books")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT author) FROM books WHERE author != 'nan'")
    authors = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT subject, COUNT(*) as count 
        FROM books 
        WHERE subject != 'nan' 
        GROUP BY subject 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_subjects = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_books': total,
        'total_authors': authors,
        'top_subjects': top_subjects
    }

def answer_with_ai(query, books_context):
    """
    استخدام Claude API للإجابة الذكية
    هذه الوظيفة تتطلب Anthropic API Key
    """
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # بناء السياق
        context = "قاعدة بيانات المكتبة:\n\n"
        for book in books_context:
            context += f"- {book['title']}"
            if book['author'] != 'nan':
                context += f" | المؤلف: {book['author']}"
            if book['subject'] != 'nan':
                context += f" | الموضوع: {book['subject']}"
            context += "\n"
        
        # إرسال الطلب لـ Claude
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""أنت مساعد مكتبة ذكي. لديك قاعدة بيانات بـ 3,931 كتاب إسلامي.

السؤال: {query}

الكتب المتاحة في قاعدة البيانات:
{context}

المطلوب:
1. أجب على السؤال بناءً على الكتب المتوفرة فقط
2. اذكر أسماء الكتب ذات الصلة
3. كن مختصراً ومفيداً
4. إذا لم تجد كتب مناسبة، اقترح كلمات بحث بديلة

الجواب:"""
                }
            ]
        )
        
        return message.content[0].text
    
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"خطأ في AI: {e}")
        return None

def format_simple_results(books):
    """تنسيق النتائج البسيطة (بدون AI)"""
    if not books:
        return "😔 لم أجد أي كتب مطابقة لبحثك."
    
    response = f"📚 وجدت **{len(books)}** كتاب:\n\n"
    
    for i, book in enumerate(books[:10], 1):
        response += f"{i}. 📖 **{book['title']}**\n"
        
        if book['author'] and book['author'] != 'nan':
            response += f"   ✍️ {book['author']}\n"
        
        if book['year'] and book['year'] != 'nan':
            response += f"   📅 {book['year']}\n"
        
        response += "\n"
    
    return response

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    welcome = """
🌟 **مرحباً بك في بوت المكتبة الإسلامية الذكي**

🧠 **مدعوم بالذكاء الاصطناعي**

📚 لدي **3,931 كتاب** جاهز للإجابة على أسئلتك!

**كيف أستخدم البوت؟**

فقط اكتب سؤالك مباشرة! مثال:
- "ابحث لي عن كتب الفقه الحنبلي"
- "من مؤلف كتاب الموافقات؟"
- "كتب في التفسير من القرن الثامن"
- "ما هي كتب ابن القيم المتوفرة؟"

**الأوامر:**
/search - بحث
/stats - الإحصائيات
/help - المساعدة

💡 البوت يفهم الأسئلة بالعربية الطبيعية!
"""
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإحصائيات"""
    stats = get_stats()
    
    text = f"""
📊 **إحصائيات المكتبة:**

📚 إجمالي الكتب: **{stats['total_books']:,}**
✍️ عدد المؤلفين: **{stats['total_authors']:,}**

🔥 **أكثر المواضيع:**
"""
    
    for i, (subject, count) in enumerate(stats['top_subjects'], 1):
        if subject and subject != 'nan':
            text += f"{i}. {subject[:50]} ({count} كتاب)\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأسئلة"""
    query = update.message.text.strip()
    
    if len(query) < 3:
        await update.message.reply_text("❌ الرجاء كتابة سؤال أطول (3 أحرف على الأقل)")
        return
    
    # إرسال رسالة الانتظار
    wait_msg = await update.message.reply_text("🔍 جاري البحث...")
    
    # البحث في قاعدة البيانات
    books = get_relevant_books(query, limit=15)
    
    # محاولة استخدام AI
    ai_response = answer_with_ai(query, books)
    
    if ai_response:
        # إجابة ذكية بالـ AI
        response = f"🧠 **إجابة ذكية:**\n\n{ai_response}"
    else:
        # إجابة بسيطة بدون AI
        response = format_simple_results(books)
    
    # حذف رسالة الانتظار
    await wait_msg.delete()
    
    # إرسال الإجابة
    await update.message.reply_text(response, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البحث"""
    if not context.args:
        await update.message.reply_text("❌ الرجاء كتابة كلمة البحث\nمثال: /search الفقه")
        return
    
    query = ' '.join(context.args)
    
    # تحديث النص ليبدو كأنه سؤال عادي
    update.message.text = query
    await handle_query(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المساعدة"""
    help_text = """
📖 **دليل الاستخدام:**

**1️⃣ اسأل مباشرة:**
لا تحتاج لأوامر! فقط اكتب سؤالك:

✅ "كتب الإمام الشافعي"
✅ "ما هي كتب التفسير المتوفرة؟"
✅ "ابحث عن الفقه المالكي"
✅ "كتب صدرت سنة 1400"

**2️⃣ أو استخدم الأوامر:**
/search كلمة البحث
/stats - الإحصائيات

**3️⃣ نصائح:**
- اكتب أسئلة واضحة
- يمكنك استخدام اسم المؤلف أو الموضوع
- البوت يفهم الأسئلة المركبة

🧠 **مدعوم بالذكاء الاصطناعي للإجابات الأذكى!**
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"خطأ: {context.error}")
    
    if update and update.message:
        await update.message.reply_text("😔 عذراً، حدث خطأ. الرجاء المحاولة مرة أخرى.")

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("search", search_command))
    
    # معالج الرسائل النصية (الأسئلة)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # تشغيل البوت
    print("🤖 البوت الذكي يعمل الآن...")
    print("🧠 مدعوم بالذكاء الاصطناعي!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
