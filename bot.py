
import logging
import logging.handlers
import random
import asyncio
import re
import time
import sys
import os
from collections import deque

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import telegram

import database

# Enable logging with file rotation
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# File handler with rotation (max 5MB, keep 3 backups)
file_handler = logging.handlers.RotatingFileHandler(
    'bot.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Bot Token from user input
TOKEN = os.getenv("BOT_TOKEN")

# Owner Telegram Handle
OWNER_TELEGRAM_HANDLE = "t.me/SKYDRAGO_N"

# Admin User IDs (replace with actual admin IDs)
ADMIN_IDS = {8608247732, 6238245383} # Example: {123456789, 987654321}

# Activation Codes and Package Details
PACKAGES = {
    "SKY30": {"name_ar": "باقة البرونز", "name_en": "Bronze Package", "name_fr": "Forfait Bronze", "duration_minutes": 30, "price": "500 دج", "save": None, "accuracy": "80%"},
    "SKYFIRE60": {"name_ar": "باقة الفضة", "name_en": "Silver Package", "name_fr": "Forfait Argent", "duration_minutes": 60, "price": "900 دج", "save": "10%", "accuracy": "85%"},
    "SKYDIAMOND3": {"name_ar": "باقة الذهب", "name_en": "Gold Package", "name_fr": "Forfait Or", "duration_minutes": 180, "price": "2000 دج", "save": "25%", "accuracy": "90%"},
    "SKYKING24": {"name_ar": "باقة البلاتينيوم", "name_en": "Platinum Package", "name_fr": "Forfait Platine", "duration_minutes": 1440, "price": "5000 دج", "save": "40%", "accuracy": "95%"},
    "SKYDRAGON1209": {"name_ar": "باقة الأسطورة", "name_en": "Legend Package", "name_fr": "Forfait Légende", "duration_minutes": 10080, "price": "15000 دج", "save": "أفضل قيمة! 🔥", "accuracy": "97%"}
}

# Localization messages
MESSAGES = {
    "ar": {
        "welcome": "━━━━━━━━━━━━━━━━━━\n🍏 Apple of Fortune AI Predictor v4.0\n━━━━━━━━━━━━━━━━━━\n\n⚡ مرحباً بك في أقوى أداة تحليل وتوقع\nلعبة Apple of Fortune على Melbet!\n\n🔐 تقنية تحليل متقدمة\n📊 دقة تصل إلى 97%\n🧬 تحليل خوارزمية RNG\n⚛️ حساب كمي للاحتمالات\n\n━━━━━━━━━━━━━━━━━━\n🔗 للبدء، أدخل معرف حساب Melbet الخاص بك:\n━━━━━━━━━━━━━━━━━━",
        "melbet_id_prompt": "معرف Melbet يجب أن يكون أرقامًا فقط. الرجاء إدخال معرف صحيح:",
        "linking_account": "🔗 جاري ربط الحساب...",
        "connecting_server": "🌐 الاتصال بسيرفر Melbet...",
        "searching_account": "🔍 البحث عن الحساب: {melbet_id}...",
        "account_linked_success": "✅ تم ربط الحساب بنجاح!",
        "start_playing_free_rounds": "يمكنك الآن بدء اللعب! لديك جولتان مجانيتان.",
        "main_menu_text": "القائمة الرئيسية:",
        "new_round_button": "🍏 جولة جديدة",
        "buy_code_button": "🛒 شراء الكود",
        "my_stats_button": "📊 إحصائياتي",
        "help_button": "❓ مساعدة",
        "my_melbet_id_button": "🔗 معرف Melbet الخاص بي",
        "back_button": "🔙 رجوع",
        "play_and_menu_text": "اختر الإجراء:",
        "help_message": "أهلاً بك في أداة توقع تفاحة الحظ!\n\nطريقة اللعب:\n1. أدخل معرف Melbet الخاص بك لربط الحساب.\n2. اضغط على \"جولة جديدة\".\n3. أدخل مبلغ الرهان.\n4. شاهد البوت وهو يختار التفاحة السليمة.\n\nالأوامر المتاحة:\n/start - بدء اللعبة\n/help - عرض هذه المساعدة\n/menu - عرض القائمة الرئيسية\n\n⚠️ تنبيه: هذه الأداة تعتمد على تحليل الاحتمالات ولا تضمن الفوز بنسبة 100%.",
        "stats_unavailable": "إحصائيات المستخدم غير متاحة في هذا الإصدار من اللعبة.",
        "your_melbet_id_is": "معرف Melbet الخاص بك هو: {melbet_id}",
        "melbet_id_not_linked": "لم يتم ربط معرف Melbet الخاص بك بعد. يرجى البدء باستخدام /start.",
        "enter_melbet_id_first": "الرجاء إدخال معرف Melbet الخاص بك أولاً للبدء.",
        "free_trial_ended": "انتهت التجربة المجانية! يرجى إدخال كود التفعيل أو شراء كود جديد.",
        "enter_code_button": "🔑 إدخال الكود",
        "enter_activation_code": "🔑 أدخل كود التفعيل:",
        "invalid_code": "❌ كود التفعيل غير صحيح. الرجاء المحاولة مرة أخرى.",
        "code_activated_unlimited": "✅ تم تفعيل كود {code} بنجاح! لديك الآن وصول غير محدود.",
        "code_activated_timed": "✅ تم تفعيل كود {code} بنجاح! لديك الآن وصول لمدة {duration}.",
        "enter_bet_amount": "الرجاء إدخال مبلغ الرهان:",
        "invalid_bet_amount": "الرجاء إدخال رقم صحيح وموجب لمبلغ الرهان (مثال: 50 أو 100 دج):",
        "connecting_protocol": "🔌 تهيئة بروتوكول الاتصال المشفر...\n[████░░░░░░] تحميل الوحدات...",
        "connecting_server_ip": "🌐 الاتصال بـ Melbet Server...\n📡 IP: 185.162.XXX.XX\n⏱ Ping: 18ms\n🔒 SSL/TLS: نشط",
        "bypassing_firewall": "🔓 تجاوز جدار الحماية...\n🛡 Firewall: Bypassed ✓\n🔑 Token: Acquired ✓",
        "injecting_query": "💉 حقن استعلام في قاعدة البيانات...\n📂 DB: melbet_rng_v3.db\n🔍 Table: apple_rounds",
        "decrypting_rng": "🧬 فك تشفير خوارزمية RNG...\n[██████░░░░] 60%\n🔐 AES-256: Decrypting...",
        "analyzing_rounds": "📊 تحليل 1,247 جولة سابقة...\n📈 Pattern: Detected\n🎯 Accuracy: Calculating...",
        "calculating_probabilities": "🧮 حساب الاحتمالات الكمية...\n[████████░░] 80%\n🧠 AI: Processing...",
        "prediction_ready": "✅ التوقع جاهز!",
        "prediction_result": "🍏 التفاحة الصحيحة هي رقم {apple_number}!\n\n⚠️ تذكر: هذه الأداة تعتمد على تحليل الاحتمالات ولا تضمن الفوز بنسبة 100%.",
        "prediction_failed": "❌ فشل التوقع. يبدو أن خوارزمية Melbet قد تغيرت قليلاً. حاول مرة أخرى.",
        "language_selection": "الرجاء اختيار لغتك المفضلة:",
        "lang_ar_button": "العربية 🇸🇦",
        "lang_en_button": "English 🇬🇧",
        "lang_fr_button": "Français 🇫🇷",
        "lang_set_success": "تم تعيين اللغة إلى العربية.",
        "packages_title": "━━━━━━━━━━━━━━━━━━\n🛒 باقات التفعيل المتاحة\n━━━━━━━━━━━━━━━━━━\n\n",
        "package_details": "⚡ {name} | {duration}\n💰 {price} {save_text}\n📊 دقة توقع: {accuracy}\n\n",
        "contact_owner": "📩 للشراء تواصل مع المالك مباشرة",
        "contact_owner_button": "تواصل مع المالك",
        "trial_expired_notification": "انتهت صلاحية باقتك التجريبية/المدفوعة. يرجى شراء كود تفعيل جديد للاستمرار في استخدام البوت.",
        "admin_panel_title": "لوحة تحكم المسؤول:",
        "generate_code_button": "توليد كود تفعيل",
        "broadcast_message_button": "إرسال رسالة جماعية",
        "view_stats_button": "عرض إحصائيات البوت",
        "manage_users_button": "إدارة المستخدمين",
        "enter_package_name": "الرجاء إدخال اسم الباقة (مثال: SKY30):",
        "code_generated": "✅ تم توليد الكود: {code} للباقة {package_name}.",
        "invalid_package_name": "❌ اسم الباقة غير صحيح.",
        "enter_broadcast_message": "الرجاء إدخال الرسالة التي تريد إرسالها لجميع المستخدمين:",
        "broadcast_sent": "✅ تم إرسال الرسالة لـ {count} مستخدم.",
        "bot_stats_message": "📊 إحصائيات البوت:\n\nعدد المستخدمين الكلي: {total_users}\nالأكواد المفعلة: {active_codes}\nالأكواد غير المستخدمة: {unused_codes}\n",
        "user_management_title": "إدارة المستخدمين:",
        "enter_user_id_to_manage": "الرجاء إدخال معرف المستخدم (User ID) لإدارته:",
        "user_not_found": "❌ المستخدم غير موجود.",
        "user_details": "تفاصيل المستخدم {user_id}:\nMelbet ID: {melbet_id}\nالحالة: {state}\nجولات مجانية متبقية: {free_rounds}\nالباقة النشطة: {active_package}\nتاريخ انتهاء الباقة: {expiry_time}\nاللغة: {lang}\nمسؤول: {is_admin}",
        "ban_user_button": "حظر المستخدم",
        "unban_user_button": "إلغاء حظر المستخدم",
        "set_admin_button": "تعيين كمسؤول",
        "remove_admin_button": "إزالة المسؤولية",
        "user_banned": "✅ تم حظر المستخدم {user_id}.",
        "user_unbanned": "✅ تم إلغاء حظر المستخدم {user_id}.",
        "user_set_admin": "✅ تم تعيين المستخدم {user_id} كمسؤول.",
        "user_removed_admin": "✅ تم إزالة مسؤولية المستخدم {user_id}.",
        "not_an_admin": "❌ أنت لست مسؤولاً لتنفيذ هذا الأمر.",
        "rate_limit_exceeded": "⚠️ لقد تجاوزت الحد المسموح به من الطلبات. يرجى المحاولة بعد قليل."
    },
    "en": {
        "welcome": "━━━━━━━━━━━━━━━━━━\n🍏 Apple of Fortune AI Predictor v4.0\n━━━━━━━━━━━━━━━━━━\n\n⚡ Welcome to the most powerful AI analysis and prediction tool\nfor the Apple of Fortune game on Melbet!\n\n🔐 Advanced analysis technology\n📊 Up to 97% accuracy\n🧬 RNG algorithm analysis\n⚛️ Quantum probability calculation\n\n━━━━━━━━━━━━━━━━━━\n🔗 To start, please enter your Melbet account ID:\n━━━━━━━━━━━━━━━━━━",
        "melbet_id_prompt": "Melbet ID must be digits only. Please enter a valid ID:",
        "linking_account": "🔗 Linking account...",
        "connecting_server": "🌐 Connecting to Melbet server...",
        "searching_account": "🔍 Searching for account: {melbet_id}...",
        "account_linked_success": "✅ Account linked successfully!",
        "start_playing_free_rounds": "You can now start playing! You have 2 free rounds.",
        "main_menu_text": "Main Menu:",
        "new_round_button": "🍏 New Round",
        "buy_code_button": "🛒 Buy Code",
        "my_stats_button": "📊 My Statistics",
        "help_button": "❓ Help",
        "my_melbet_id_button": "🔗 My Melbet ID",
        "back_button": "🔙 Back",
        "play_and_menu_text": "Choose an action:",
        "help_message": "Welcome to the Apple of Fortune prediction tool!\n\nHow to play:\n1. Enter your Melbet ID to link the account.\n2. Click \"New Round\".\n3. Enter the bet amount.\n4. Watch the bot choose the correct apple.\n\nAvailable commands:\n/start - Start the game\n/help - Show this help\n/menu - Show main menu\n\n⚠️ Disclaimer: This tool relies on probability analysis and does not guarantee 100% winning.",
        "stats_unavailable": "User statistics are not available in this version of the game.",
        "your_melbet_id_is": "Your Melbet ID is: {melbet_id}",
        "melbet_id_not_linked": "Your Melbet ID is not linked yet. Please start with /start.",
        "enter_melbet_id_first": "Please enter your Melbet ID first to start.",
        "free_trial_ended": "Free trial ended! Please enter an activation code or buy a new one.",
        "enter_code_button": "🔑 Enter Code",
        "enter_activation_code": "🔑 Enter activation code:",
        "invalid_code": "❌ Invalid activation code. Please try again.",
        "code_activated_unlimited": "✅ Code {code} activated successfully! You now have unlimited access.",
        "code_activated_timed": "✅ Code {code} activated successfully! You now have access for {duration}.",
        "enter_bet_amount": "Please enter the bet amount:",
        "invalid_bet_amount": "Please enter a valid positive number for the bet amount (e.g., 50 or 100):",
        "connecting_protocol": "🔌 Initializing encrypted communication protocol...\n[████░░░░░░] Loading modules...",
        "connecting_server_ip": "🌐 Connecting to Melbet Server...\n📡 IP: 185.162.XXX.XX\n⏱ Ping: 18ms\n🔒 SSL/TLS: Active",
        "bypassing_firewall": "🔓 Bypassing firewall...\n🛡 Firewall: Bypassed ✓\n🔑 Token: Acquired ✓",
        "injecting_query": "💉 Injecting query into database...\n📂 DB: melbet_rng_v3.db\n🔍 Table: apple_rounds",
        "decrypting_rng": "🧬 Decrypting RNG algorithm...\n[██████░░░░] 60%\n🔐 AES-256: Decrypting...",
        "analyzing_rounds": "📊 Analyzing 1,247 previous rounds...\n📈 Pattern: Detected\n🎯 Accuracy: Calculating...",
        "calculating_probabilities": "🧮 Calculating quantum probabilities...\n[████████░░] 80%\n🧠 AI: Processing...",
        "prediction_ready": "✅ Prediction ready!",
        "prediction_result": "🍏 The correct apple is number {apple_number}!\n\n⚠️ Remember: This tool relies on probability analysis and does not guarantee 100% winning.",
        "prediction_failed": "❌ Prediction failed. It seems Melbet\'s algorithm has slightly changed. Please try again.",
        "language_selection": "Please choose your preferred language:",
        "lang_ar_button": "العربية 🇸🇦",
        "lang_en_button": "English 🇬🇧",
        "lang_fr_button": "Français 🇫🇷",
        "lang_set_success": "Language set to English.",
        "packages_title": "━━━━━━━━━━━━━━━━━━\n🛒 Available Activation Packages\n━━━━━━━━━━━━━━━━━━\n\n",
        "package_details": "⚡ {name} | {duration}\n💰 {price} {save_text}\n📊 Prediction Accuracy: {accuracy}\n\n",
        "contact_owner": "📩 To purchase, contact the owner directly",
        "contact_owner_button": "Contact Owner",
        "trial_expired_notification": "Your trial/paid package has expired. Please purchase a new activation code to continue using the bot.",
        "admin_panel_title": "Admin Control Panel:",
        "generate_code_button": "Generate Activation Code",
        "broadcast_message_button": "Broadcast Message",
        "view_stats_button": "View Bot Statistics",
        "manage_users_button": "Manage Users",
        "enter_package_name": "Please enter package name (e.g., SKY30):",
        "code_generated": "✅ Code generated: {code} for package {package_name}.",
        "invalid_package_name": "❌ Invalid package name.",
        "enter_broadcast_message": "Please enter the message you want to send to all users:",
        "broadcast_sent": "✅ Message sent to {count} users.",
        "bot_stats_message": "📊 Bot Statistics:\n\nTotal Users: {total_users}\nActivated Codes: {active_codes}\nUnused Codes: {unused_codes}\n",
        "user_management_title": "User Management:",
        "enter_user_id_to_manage": "Please enter the User ID to manage:",
        "user_not_found": "❌ User not found.",
        "user_details": "User {user_id} Details:\nMelbet ID: {melbet_id}\nStatus: {state}\nFree Rounds Remaining: {free_rounds}\nActive Package: {active_package}\nPackage Expiry: {expiry_time}\nLanguage: {lang}\nAdmin: {is_admin}",
        "ban_user_button": "Ban User",
        "unban_user_button": "Unban User",
        "set_admin_button": "Set as Admin",
        "remove_admin_button": "Remove Admin Status",
        "user_banned": "✅ User {user_id} banned.",
        "user_unbanned": "✅ User {user_id} unbanned.",
        "user_set_admin": "✅ User {user_id} set as admin.",
        "user_removed_admin": "✅ User {user_id} removed from admin status.",
        "not_an_admin": "❌ You are not an administrator to perform this command.",
        "rate_limit_exceeded": "⚠️ You have exceeded the request limit. Please try again shortly."
    },
    "fr": {
        "welcome": "━━━━━━━━━━━━━━━━━━\n🍏 Apple of Fortune AI Predictor v4.0\n━━━━━━━━━━━━━━━━━━\n\n⚡ Bienvenue dans l\'outil d\'analyse et de prédiction IA le plus puissant\npour le jeu Apple of Fortune sur Melbet !\n\n🔐 Technologie d\'analyse avancée\n📊 Précision jusqu\'à 97%\n🧬 Analyse de l\'algorithme RNG\n⚛️ Calcul de probabilité quantique\n\n━━━━━━━━━━━━━━━━━━\n🔗 Pour commencer, veuillez entrer votre identifiant de compte Melbet :\n━━━━━━━━━━━━━━━━━━",
        "melbet_id_prompt": "L\'identifiant Melbet doit contenir uniquement des chiffres. Veuillez entrer un identifiant valide :",
        "linking_account": "🔗 Liaison du compte...",
        "connecting_server": "🌐 Connexion au serveur Melbet...",
        "searching_account": "🔍 Recherche du compte : {melbet_id}...",
        "account_linked_success": "✅ Compte lié avec succès !",
        "start_playing_free_rounds": "Vous pouvez maintenant commencer à jouer ! Vous avez 2 tours gratuits.",
        "main_menu_text": "Menu principal :",
        "new_round_button": "🍏 Nouvelle Partie",
        "buy_code_button": "🛒 Acheter un Code",
        "my_stats_button": "📊 Mes Statistiques",
        "help_button": "❓ Aide",
        "my_melbet_id_button": "🔗 Mon identifiant Melbet",
        "back_button": "🔙 Retour",
        "play_and_menu_text": "Choisissez une action :",
        "help_message": "Bienvenue dans l\'outil de prédiction Apple of Fortune !\n\nComment jouer :\n1. Entrez votre identifiant Melbet pour lier le compte.\n2. Cliquez sur \"Nouvelle Partie\".\n3. Entrez le montant de la mise.\n4. Regardez le bot choisir la bonne pomme.\n\nCommandes disponibles :\n/start - Démarrer le jeu\n/help - Afficher cette aide\n/menu - Afficher le menu principal\n\n⚠️ Avertissement : Cet outil repose sur l\'analyse des probabilités et ne garantit pas un gain à 100 %.",
        "stats_unavailable": "Les statistiques utilisateur ne sont pas disponibles dans cette version du jeu.",
        "your_melbet_id_is": "Votre identifiant Melbet est : {melbet_id}",
        "melbet_id_not_linked": "Votre identifiant Melbet n\'est pas encore lié. Veuillez commencer par /start.",
        "enter_melbet_id_first": "Veuillez d\'abord entrer votre identifiant Melbet pour commencer.",
        "free_trial_ended": "Essai gratuit terminé ! Veuillez entrer un code d\'activation ou en acheter un nouveau.",
        "enter_code_button": "🔑 Entrer le Code",
        "enter_activation_code": "🔑 Entrez le code d\'activation :",
        "invalid_code": "❌ Code d\'activation invalide. Veuillez réessayer.",
        "code_activated_unlimited": "✅ Code {code} activé avec succès ! Vous avez maintenant un accès illimité.",
        "code_activated_timed": "✅ Code {code} activé avec succès ! Vous avez maintenant accès pour {duration}.",
        "enter_bet_amount": "Veuillez entrer le montant de la mise :",
        "invalid_bet_amount": "Veuillez entrer un nombre positif valide pour le montant de la mise (ex: 50 ou 100) :",
        "connecting_protocol": "🔌 Initialisation du protocole de communication chiffré...\n[████░░░░░░] Chargement des modules...",
        "connecting_server_ip": "🌐 Connexion au serveur Melbet...\n📡 IP: 185.162.XXX.XX\n⏱ Ping: 18ms\n🔒 SSL/TLS: Actif",
        "bypassing_firewall": "🔓 Contournement du pare-feu...\n🛡 Pare-feu : Contourné ✓\n🔑 Jeton : Acquis ✓",
        "injecting_query": "💉 Injection de requête dans la base de données...\n📂 DB: melbet_rng_v3.db\n🔍 Table: apple_rounds",
        "decrypting_rng": "🧬 Déchiffrement de l\'algorithme RNG...\n[██████░░░░] 60%\n🔐 AES-256 : Déchiffrement...",
        "analyzing_rounds": "📊 Analyse de 1 247 tours précédents...\n📈 Motif : Détecté\n🎯 Précision : Calcul en cours...",
        "calculating_probabilities": "🧮 Calcul des probabilités quantiques...\n[████████░░] 80%\n🧠 IA : Traitement...",
        "prediction_ready": "✅ Prédiction prête !",
        "prediction_result": "🍏 La bonne pomme est le numéro {apple_number} !\n\n⚠️ Rappel : Cet outil repose sur l\'analyse des probabilités et ne garantit pas un gain à 100 %.",
        "prediction_failed": "❌ Prédiction échouée. Il semble que l\'algorithme de Melbet ait légèrement changé. Veuillez réessayer.",
        "language_selection": "Veuillez choisir votre langue préférée :",
        "lang_ar_button": "العربية 🇸🇦",
        "lang_en_button": "English 🇬🇧",
        "lang_fr_button": "Français 🇫🇷",
        "lang_set_success": "Langue définie sur Français.",
        "packages_title": "━━━━━━━━━━━━━━━━━━\n🛒 Forfaits d\'activation disponibles\n━━━━━━━━━━━━━━━━━━\n\n",
        "package_details": "⚡ {name} | {duration}\n💰 {price} {save_text}\n📊 Précision de la prédiction : {accuracy}\n\n",
        "contact_owner": "📩 Pour acheter, contactez directement le propriétaire",
        "contact_owner_button": "Contacter le propriétaire",
        "trial_expired_notification": "Votre forfait d\'essai/payant a expiré. Veuillez acheter un nouveau code d\'activation pour continuer à utiliser le bot.",
        "admin_panel_title": "Panneau de contrôle administrateur :",
        "generate_code_button": "Générer un code d\'activation",
        "broadcast_message_button": "Diffuser un message",
        "view_stats_button": "Afficher les statistiques du bot",
        "manage_users_button": "Gérer les utilisateurs",
        "enter_package_name": "Veuillez entrer le nom du forfait (ex: SKY30) :",
        "code_generated": "✅ Code généré : {code} pour le forfait {package_name}.",
        "invalid_package_name": "❌ Nom de forfait invalide.",
        "enter_broadcast_message": "Veuillez entrer le message que vous souhaitez envoyer à tous les utilisateurs :",
        "broadcast_sent": "✅ Message envoyé à {count} utilisateurs.",
        "bot_stats_message": "📊 Statistiques du bot :\n\nTotal des utilisateurs : {total_users}\nCodes activés : {active_codes}\nCodes inutilisés : {unused_codes}\n",
        "user_management_title": "Gestion des utilisateurs :",
        "enter_user_id_to_manage": "Veuillez entrer l\'ID utilisateur à gérer :",
        "user_not_found": "❌ Utilisateur introuvable.",
        "user_details": "Détails de l\'utilisateur {user_id} :\nID Melbet : {melbet_id}\nStatut : {state}\nParties gratuites restantes : {free_rounds}\nForfait actif : {active_package}\nExpiration du forfait : {expiry_time}\nLangue : {lang}\nAdmin : {is_admin}",
        "ban_user_button": "Bannir l\'utilisateur",
        "unban_user_button": "Débannir l\'utilisateur",
        "set_admin_button": "Définir comme administrateur",
        "remove_admin_button": "Supprimer le statut d\'administrateur",
        "user_banned": "✅ Utilisateur {user_id} banni.",
        "user_unbanned": "✅ Utilisateur {user_id} débanni.",
        "user_set_admin": "✅ Utilisateur {user_id} défini comme administrateur.",
        "user_removed_admin": "✅ Utilisateur {user_id} retiré du statut d\'administrateur.",
        "not_an_admin": "❌ Vous n\'êtes pas un administrateur pour exécuter cette commande.",
        "rate_limit_exceeded": "⚠️ Vous avez dépassé la limite de requêtes. Veuillez réessayer sous peu."
    }
}

# Rate limiting (anti-spam)
LAST_REQUEST_TIME = {}
RATE_LIMIT_SECONDS = 1 # 1 second between requests per user

def get_text(user_id, key):
    user = database.get_user(user_id)
    lang = user["lang"] if user else "ar" # Default to Arabic
    return MESSAGES.get(lang, MESSAGES["ar"]).get(key, MESSAGES["ar"][key])

def get_main_menu_keyboard(user_id) -> InlineKeyboardMarkup:
    lang = database.get_user(user_id)["lang"]
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "new_round_button"), callback_data="new_round")],
        [InlineKeyboardButton(get_text(user_id, "buy_code_button"), callback_data="buy_code")],
        [InlineKeyboardButton(get_text(user_id, "my_stats_button"), callback_data="show_stats")],
        [InlineKeyboardButton(get_text(user_id, "help_button"), callback_data="show_help")],
        [InlineKeyboardButton(get_text(user_id, "my_melbet_id_button"), callback_data="show_melbet_id")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_play_and_menu_keyboard(user_id) -> InlineKeyboardMarkup:
    lang = database.get_user(user_id)["lang"]
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "new_round_button"), callback_data="new_round")],
        [InlineKeyboardButton(get_text(user_id, "main_menu_text"), callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_menu_keyboard(user_id) -> InlineKeyboardMarkup:
    lang = database.get_user(user_id)["lang"]
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "back_button"), callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    user = database.get_user(user_id)

    # Always show welcome message first
    await update.message.reply_text(get_text(user_id, "welcome"))

    # If user already has a Melbet ID linked, also show the main menu
    if user["state"] != "waiting_for_melbet_id":
        await update.message.reply_text(get_text(user_id, "main_menu_text"), reply_markup=get_main_menu_keyboard(user_id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await update.message.reply_text(get_text(user_id, "help_message"), reply_markup=get_back_to_menu_keyboard(user_id))

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await update.message.reply_text(get_text(user_id, "main_menu_text"), reply_markup=get_main_menu_keyboard(user_id))

async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await query.edit_message_text(get_text(user_id, "stats_unavailable"), reply_markup=get_back_to_menu_keyboard(user_id))

async def show_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await query.edit_message_text(get_text(user_id, "help_message"), reply_markup=get_back_to_menu_keyboard(user_id))

async def show_melbet_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    user = database.get_user(user_id)
    if user and user["melbet_id"]:
        await query.edit_message_text(get_text(user_id, "your_melbet_id_is").format(melbet_id=user["melbet_id"]), reply_markup=get_back_to_menu_keyboard(user_id))
    else:
        await query.edit_message_text(get_text(user_id, "melbet_id_not_linked"), reply_markup=get_back_to_menu_keyboard(user_id))

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await query.edit_message_text(get_text(user_id, "main_menu_text"), reply_markup=get_main_menu_keyboard(user_id))

async def new_round_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    user = database.get_user(user_id)

    if not user or user["state"] == "waiting_for_melbet_id":
        await query.edit_message_text(get_text(user_id, "enter_melbet_id_first"))
        return

    current_time = int(time.time())
    if user["active_package"] and user["package_expiry_time"] > current_time:
        # User has an active paid package
        database.create_or_update_user(user_id, state="waiting_for_bet")
        await query.edit_message_text(get_text(user_id, "enter_bet_amount"), reply_markup=get_back_to_menu_keyboard(user_id))
    elif user["free_rounds_remaining"] > 0:
        # User has free rounds remaining
        database.create_or_update_user(user_id, state="waiting_for_bet")
        await query.edit_message_text(get_text(user_id, "enter_bet_amount"), reply_markup=get_back_to_menu_keyboard(user_id))
    else:
        # Free trial ended and no active package
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "enter_code_button"), callback_data="enter_code")],
            [InlineKeyboardButton(get_text(user_id, "buy_code_button"), callback_data="buy_code")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(get_text(user_id, "free_trial_ended"), reply_markup=reply_markup)
        database.create_or_update_user(user_id, state="locked")

async def enter_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    await query.edit_message_text(get_text(user_id, "enter_activation_code"), reply_markup=get_back_to_menu_keyboard(user_id))
    database.create_or_update_user(user_id, state="waiting_for_code")

async def buy_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    user_lang = database.get_user(user_id)["lang"]

    packages_text = get_text(user_id, "packages_title")
    for code, details in PACKAGES.items():
        name = details[f"name_{user_lang}"]
        duration = details["duration_minutes"]
        if duration >= 1440: # Days
            duration_str = f"{duration // 1440} {'يوم' if user_lang == 'ar' else 'day' if user_lang == 'en' else 'jour'}"
        elif duration >= 60: # Hours
            duration_str = f"{duration // 60} {'ساعة' if user_lang == 'ar' else 'hour' if user_lang == 'en' else 'heure'}"
        else:
            duration_str = f"{duration} {'دقيقة' if user_lang == 'ar' else 'minute' if user_lang == 'en' else 'minute'}"

        save_text = f"({details['save']})" if details["save"] else ""
        packages_text += get_text(user_id, "package_details").format(
            name=name,
            duration=duration_str,
            price=details["price"],
            save_text=save_text,
            accuracy=details["accuracy"]
        )

    packages_text += get_text(user_id, "contact_owner")

    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "contact_owner_button"), url=OWNER_TELEGRAM_HANDLE)],
        [InlineKeyboardButton(get_text(user_id, "back_button"), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(packages_text, reply_markup=reply_markup)

def extract_bet_amount(text: str) -> int | None:
    numbers = re.findall(r"\d+", text)
    if numbers:
        return int(numbers[0])
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text

    # Rate limiting
    current_time = time.time()
    if user_id in LAST_REQUEST_TIME and (current_time - LAST_REQUEST_TIME[user_id]) < RATE_LIMIT_SECONDS:
        await update.message.reply_text(get_text(user_id, "rate_limit_exceeded"))
        return
    LAST_REQUEST_TIME[user_id] = current_time

    database.create_or_update_user(user_id, last_activity=int(current_time))
    user = database.get_user(user_id)

    if not user:
        await start(update, context) # Restart flow if user data is missing
        return

    if user["state"] == "waiting_for_melbet_id":
        melbet_id = user_message.strip()
        if not melbet_id.isdigit():
            await update.message.reply_text(get_text(user_id, "melbet_id_prompt"))
            return

        database.create_or_update_user(user_id, melbet_id=melbet_id, state="active")

        # Dramatic linking effects
        message = await update.message.reply_text(get_text(user_id, "linking_account"))
        await asyncio.sleep(1.0)
        await message.edit_text(get_text(user_id, "connecting_server"))
        await asyncio.sleep(1.0)
        await message.edit_text(get_text(user_id, "searching_account").format(melbet_id=melbet_id))
        await asyncio.sleep(1.0)
        await message.edit_text(get_text(user_id, "account_linked_success"))
        await asyncio.sleep(0.5)

        await update.message.reply_text(get_text(user_id, "start_playing_free_rounds"), reply_markup=get_play_and_menu_keyboard(user_id))
        return

    if user["state"] == "waiting_for_code":
        entered_code = user_message.strip().upper()
        code_data = database.get_activation_code(entered_code)

        if code_data and not code_data["is_used"]:
            duration_minutes = code_data["duration_minutes"]
            expiry_time = 0
            duration_str = "unlimited"

            if duration_minutes > 0:
                expiry_time = int(time.time()) + duration_minutes * 60
                if duration_minutes >= 1440: # Days
                    duration_str = f"{duration_minutes // 1440} {'يوم' if user['lang'] == 'ar' else 'day' if user['lang'] == 'en' else 'jour'}"
                elif duration_minutes >= 60: # Hours
                    duration_str = f"{duration_minutes // 60} {'ساعة' if user['lang'] == 'ar' else 'hour' if user['lang'] == 'en' else 'heure'}"
                else:
                    duration_str = f"{duration_minutes} {'دقيقة' if user['lang'] == 'ar' else 'minute' if user['lang'] == 'en' else 'minute'}"

            database.use_activation_code(entered_code, user_id)
            database.create_or_update_user(user_id, state="active", free_rounds_remaining=-1, active_package=entered_code, package_expiry_time=expiry_time)

            if duration_minutes > 0:
                await update.message.reply_text(get_text(user_id, "code_activated_timed").format(code=entered_code, duration=duration_str), reply_markup=get_play_and_menu_keyboard(user_id))
            else:
                await update.message.reply_text(get_text(user_id, "code_activated_unlimited").format(code=entered_code), reply_markup=get_play_and_menu_keyboard(user_id))
        else:
            await update.message.reply_text(get_text(user_id, "invalid_code"), reply_markup=get_back_to_menu_keyboard(user_id))
        return

    if user["state"] == "waiting_for_bet":
        bet_amount = extract_bet_amount(user_message)
        if bet_amount is None or bet_amount <= 0:
            await update.message.reply_text(get_text(user_id, "invalid_bet_amount"))
            return

        # Check for expired package
        current_time = int(time.time())
        if user["active_package"] and user["package_expiry_time"] > 0 and user["package_expiry_time"] <= current_time:
            database.create_or_update_user(user_id, state="locked", active_package=None, package_expiry_time=0)
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "enter_code_button"), callback_data="enter_code")],
                [InlineKeyboardButton(get_text(user_id, "buy_code_button"), callback_data="buy_code")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(get_text(user_id, "trial_expired_notification"), reply_markup=reply_markup)
            return

        # Prediction logic with win/loss ratio control
        is_win = False
        if user["free_rounds_remaining"] > 0:
            # First 2 free rounds are always a win
            is_win = True
            database.create_or_update_user(user_id, free_rounds_remaining=user["free_rounds_remaining"] - 1)
        elif user["active_package"]:
            # Use accuracy from package details
            package_accuracy_str = PACKAGES[user["active_package"]]["accuracy"]
            accuracy_percentage = int(package_accuracy_str.replace("%", ""))
            is_win = random.randint(1, 100) <= accuracy_percentage
        else:
            # Fallback for any other case (shouldn't happen if states are managed correctly)
            is_win = random.choice([True, False])

        database.create_or_update_user(user_id, state="active") # Reset state after receiving bet

        # Dramatic hacking effects
        message = await update.message.reply_text(get_text(user_id, "connecting_protocol"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "connecting_server_ip"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "bypassing_firewall"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "injecting_query"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "decrypting_rng"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "analyzing_rounds"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "calculating_probabilities"))
        await asyncio.sleep(1.5)
        await message.edit_text(get_text(user_id, "prediction_ready"))
        await asyncio.sleep(0.5)

        if is_win:
            predicted_apple = random.randint(1, 5) # Apple of Fortune usually has 5 apples
            await update.message.reply_text(get_text(user_id, "prediction_result").format(apple_number=predicted_apple), reply_markup=get_play_and_menu_keyboard(user_id))
        else:
            await update.message.reply_text(get_text(user_id, "prediction_failed"), reply_markup=get_play_and_menu_keyboard(user_id))
        return

    # Admin commands handler
    if user_id in ADMIN_IDS and user_message.startswith("/admin"):
        await admin_panel(update, context)
        return

    # Default message for unhandled states or messages
    await update.message.reply_text(get_text(user_id, "main_menu_text"), reply_markup=get_main_menu_keyboard(user_id))

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    database.create_or_update_user(user_id, last_activity=int(time.time()))
    keyboard = [
        [InlineKeyboardButton(MESSAGES["ar"]["lang_ar_button"], callback_data="set_lang_ar")],
        [InlineKeyboardButton(MESSAGES["en"]["lang_en_button"], callback_data="set_lang_en")],
        [InlineKeyboardButton(MESSAGES["fr"]["lang_fr_button"], callback_data="set_lang_fr")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(user_id, "language_selection"), reply_markup=reply_markup)

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang_code = query.data.replace("set_lang_", "")
    database.create_or_update_user(user_id, lang=lang_code, last_activity=int(time.time()))
    await query.edit_message_text(get_text(user_id, "lang_set_success"), reply_markup=get_main_menu_keyboard(user_id))

# Admin Panel Handlers
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(get_text(user_id, "not_an_admin"))
        return

    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "generate_code_button"), callback_data="admin_generate_code")],
        [InlineKeyboardButton(get_text(user_id, "broadcast_message_button"), callback_data="admin_broadcast")],
        [InlineKeyboardButton(get_text(user_id, "view_stats_button"), callback_data="admin_view_stats")],
        [InlineKeyboardButton(get_text(user_id, "manage_users_button"), callback_data="admin_manage_users")],
        [InlineKeyboardButton(get_text(user_id, "back_button"), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(user_id, "admin_panel_title"), reply_markup=reply_markup)

async def admin_generate_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text(get_text(user_id, "not_an_admin"))
        return
    await query.edit_message_text(get_text(user_id, "enter_package_name"), reply_markup=get_back_to_menu_keyboard(user_id))
    database.create_or_update_user(user_id, state="admin_waiting_for_package_name")

async def admin_handle_generate_code_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(get_text(user_id, "not_an_admin"))
        return

    user = database.get_user(user_id)
    if user["state"] == "admin_waiting_for_package_name":
        package_name = update.message.text.strip().upper()
        if package_name in PACKAGES:
            new_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
            duration = PACKAGES[package_name]["duration_minutes"]
            database.create_activation_code(new_code, package_name, duration)
            await update.message.reply_text(get_text(user_id, "code_generated").format(code=new_code, package_name=package_name), reply_markup=get_back_to_menu_keyboard(user_id))
            database.create_or_update_user(user_id, state="active") # Reset admin state
        else:
            await update.message.reply_text(get_text(user_id, "invalid_package_name"), reply_markup=get_back_to_menu_keyboard(user_id))

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text(get_text(user_id, "not_an_admin"))
        return
    await query.edit_message_text(get_text(user_id, "enter_broadcast_message"), reply_markup=get_back_to_menu_keyboard(user_id))
    database.create_or_update_user(user_id, state="admin_waiting_for_broadcast_message")

async def admin_handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(get_text(user_id, "not_an_admin"))
        return

    user = database.get_user(user_id)
    if user["state"] == "admin_waiting_for_broadcast_message":
        message_to_send = update.message.text
        all_users = database.get_all_users()
        sent_count = 0
        for target_user_id in all_users:
            try:
                await context.bot.send_message(chat_id=target_user_id, text=message_to_send)
                sent_count += 1
                await asyncio.sleep(0.05) # Small delay to avoid hitting Telegram API limits
            except Exception as e:
                logger.warning(f"Could not send broadcast message to user {target_user_id}: {e}")
        await update.message.reply_text(get_text(user_id, "broadcast_sent").format(count=sent_count), reply_markup=get_back_to_menu_keyboard(user_id))
        database.create_or_update_user(user_id, state="active") # Reset admin state

async def admin_view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text(get_text(user_id, "not_an_admin"))
        return

    total_users = len(database.get_all_users())
    all_codes = database.get_all_active_codes() # This actually gets all codes, used or not
    active_codes = sum(1 for code in all_codes if code["is_used"])
    unused_codes = sum(1 for code in all_codes if not code["is_used"])

    stats_message = get_text(user_id, "bot_stats_message").format(
        total_users=total_users,
        active_codes=active_codes,
        unused_codes=unused_codes
    )
    await query.edit_message_text(stats_message, reply_markup=get_back_to_menu_keyboard(user_id))

async def admin_manage_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text(get_text(user_id, "not_an_admin"))
        return
    await query.edit_message_text(get_text(user_id, "enter_user_id_to_manage"), reply_markup=get_back_to_menu_keyboard(user_id))
    database.create_or_update_user(user_id, state="admin_waiting_for_user_id_to_manage")

async def admin_handle_user_id_to_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(get_text(user_id, "not_an_admin"))
        return

    user = database.get_user(user_id)
    if user["state"] == "admin_waiting_for_user_id_to_manage":
        target_user_id_str = update.message.text.strip()
        if not target_user_id_str.isdigit():
            await update.message.reply_text(get_text(user_id, "enter_user_id_to_manage"), reply_markup=get_back_to_menu_keyboard(user_id))
            return
        target_user_id = int(target_user_id_str)
        target_user = database.get_user(target_user_id)

        if not target_user:
            await update.message.reply_text(get_text(user_id, "user_not_found"), reply_markup=get_back_to_menu_keyboard(user_id))
            database.create_or_update_user(user_id, state="active")
            return

        context.user_data["admin_target_user_id"] = target_user_id

        expiry_time_str = "N/A"
        if target_user["package_expiry_time"] > 0:
            expiry_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target_user["package_expiry_time"]))

        user_details_message = get_text(user_id, "user_details").format(
            user_id=target_user_id,
            melbet_id=target_user["melbet_id"],
            state=target_user["state"],
            free_rounds=target_user["free_rounds_remaining"],
            active_package=target_user["active_package"],
            expiry_time=expiry_time_str,
            lang=target_user["lang"],
            is_admin=target_user["is_admin"]
        )

        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "ban_user_button"), callback_data=f"admin_ban_user_{target_user_id}")],
            [InlineKeyboardButton(get_text(user_id, "unban_user_button"), callback_data=f"admin_unban_user_{target_user_id}")],
            [InlineKeyboardButton(get_text(user_id, "set_admin_button"), callback_data=f"admin_set_admin_{target_user_id}")],
            [InlineKeyboardButton(get_text(user_id, "remove_admin_button"), callback_data=f"admin_remove_admin_{target_user_id}")],
            [InlineKeyboardButton(get_text(user_id, "back_button"), callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(user_details_message, reply_markup=reply_markup)
        database.create_or_update_user(user_id, state="active") # Reset admin state

async def admin_user_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    admin_user_id = query.from_user.id
    if admin_user_id not in ADMIN_IDS:
        await query.edit_message_text(get_text(admin_user_id, "not_an_admin"))
        return

    action_data = query.data.split("_")
    action_type = action_data[1]
    target_user_id = int(action_data[2])

    if action_type == "ban":
        database.create_or_update_user(target_user_id, state="banned")
        await query.edit_message_text(get_text(admin_user_id, "user_banned").format(user_id=target_user_id), reply_markup=get_back_to_menu_keyboard(admin_user_id))
    elif action_type == "unban":
        database.create_or_update_user(target_user_id, state="active") # Or previous state
        await query.edit_message_text(get_text(admin_user_id, "user_unbanned").format(user_id=target_user_id), reply_markup=get_back_to_menu_keyboard(admin_user_id))
    elif action_type == "set":
        database.create_or_update_user(target_user_id, is_admin=True)
        ADMIN_IDS.add(target_user_id) # Add to in-memory admin list
        await query.edit_message_text(get_text(admin_user_id, "user_set_admin").format(user_id=target_user_id), reply_markup=get_back_to_menu_keyboard(admin_user_id))
    elif action_type == "remove":
        database.create_or_update_user(target_user_id, is_admin=False)
        ADMIN_IDS.discard(target_user_id) # Remove from in-memory admin list
        await query.edit_message_text(get_text(admin_user_id, "user_removed_admin").format(user_id=target_user_id), reply_markup=get_back_to_menu_keyboard(admin_user_id))


def main() -> None:
    """Start the bot."""
    # Build application with robust timeout and retry settings
    request = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        connection_pool_size=8
    )
    application = Application.builder().token(TOKEN).request(request).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("admin", admin_panel)) # Admin entry point

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(new_round_callback, pattern="^new_round$"))
    application.add_handler(CallbackQueryHandler(buy_code_callback, pattern="^buy_code$"))
    application.add_handler(CallbackQueryHandler(show_stats_callback, pattern="^show_stats$"))
    application.add_handler(CallbackQueryHandler(show_help_callback, pattern="^show_help$"))
    application.add_handler(CallbackQueryHandler(show_melbet_id_callback, pattern="^show_melbet_id$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(enter_code_callback, pattern="^enter_code$"))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_lang_(ar|en|fr)$"))

    # Admin callback handlers
    application.add_handler(CallbackQueryHandler(admin_generate_code_callback, pattern="^admin_generate_code$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_view_stats_callback, pattern="^admin_view_stats$"))
    application.add_handler(CallbackQueryHandler(admin_manage_users_callback, pattern="^admin_manage_users$"))
    application.add_handler(CallbackQueryHandler(admin_user_action_callback, pattern="^admin_(ban|unban|set|remove)_user_\\d+$"))

    # Message handler for states
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot with robust settings
    logger.info("Bot started successfully!")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,
        drop_pending_updates=True
    )


def run_with_auto_restart():
    """Wrapper that auto-restarts the bot on any crash with exponential backoff."""
    restart_delay = 5  # Start with 5 seconds
    max_delay = 300  # Max 5 minutes between restarts
    consecutive_failures = 0

    while True:
        try:
            logger.info(f"Starting bot... (attempt after {consecutive_failures} failures)")
            main()
            # If main() returns normally, reset counter
            consecutive_failures = 0
            restart_delay = 5
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            sys.exit(0)
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Bot crashed with error: {e}. Restarting in {restart_delay}s...")
            time.sleep(restart_delay)
            # Exponential backoff
            restart_delay = min(restart_delay * 2, max_delay)


if __name__ == "__main__":
    # Initialize database
    database.init_db()
    run_with_auto_restart()
