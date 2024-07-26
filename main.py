import asyncio
import logging
import sys
from os import getenv

from aiogram import F, Dispatcher, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN = getenv('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_states = {}

first_lesson_keyboard = InlineKeyboardBuilder()
first_lesson_keyboard.row(InlineKeyboardButton(text="Darsni ko'rish📹", url='http://jahongirprank.uz/1-darslik/'))
first_lesson_keyboard.adjust(1)

second_lesson_keyboard = InlineKeyboardBuilder()
second_lesson_keyboard.row(InlineKeyboardButton(text="Darsni ko'rish📹", url='http://jahongirprank.uz/2-darslik/'))
second_lesson_keyboard.adjust(1)

third_lesson_keyboard = InlineKeyboardBuilder()
third_lesson_keyboard.row(InlineKeyboardButton(text="Darsni ko'rish📹", url='http://jahongirprank.uz/3-darslik/'))
third_lesson_keyboard.adjust(1)

fourth_lesson_keyboard = InlineKeyboardBuilder()
fourth_lesson_keyboard.row(InlineKeyboardButton(text="Darsni ko'rish📹", url='http://jahongirprank.uz/4-darslik/'))
fourth_lesson_keyboard.adjust(1)

fr_reminder_keyboard = InlineKeyboardBuilder()
fr_reminder_keyboard.row(InlineKeyboardButton(text="Ha ko'rdim, bonus dars bering!", callback_data="second_lesson"))
fr_reminder_keyboard.row(InlineKeyboardButton(text="Yo'q, hoziroq ko'raman", callback_data='watch_first_lesson'))

sr_reminder_keyboard = InlineKeyboardBuilder()
sr_reminder_keyboard.row(InlineKeyboardButton(text="Darsni ko'rdim", callback_data="third_lesson"))
sr_reminder_keyboard.row(InlineKeyboardButton(text="Darsni ko'rish😍", callback_data="watch_second_lesson"))

tr_reminder_keyboard = InlineKeyboardBuilder()
tr_reminder_keyboard.row(InlineKeyboardButton(text="Ha ko'rdim, bonus dars bering!", callback_data="fourth_lesson"))
tr_reminder_keyboard.row(InlineKeyboardButton(text="Yo'q, hoziroq ko'raman", callback_data="watch_third_lesson"))

for_reminder_keyboard = InlineKeyboardBuilder()
for_reminder_keyboard.row(InlineKeyboardButton(text="Ha, anketani bering", callback_data="google_form"))
for_reminder_keyboard.row(InlineKeyboardButton(text="Videoni endi ko'raman", callback_data="watch_fourth_lesson"))

google_form_k = InlineKeyboardBuilder()
google_form_k.row(InlineKeyboardButton(text="Anketani to'ldirish", url="https://forms.gle/6HCyDD4QBwqrXWNF8"))
google_form_k.adjust(1)

admin = InlineKeyboardBuilder()
admin.row(InlineKeyboardButton(text='Admin', url='@JahongirPrankAdmin'))


async def send_message_after_delay(chat_id, delay_minutes, message=None, video=None, video_note=None, audio=None,
                                   image=None, reply_markup=None):
    try:
        await asyncio.sleep(delay_minutes * 60)
        if message:
            await bot.send_message(chat_id, message, reply_markup=reply_markup)
        if video:
            await bot.send_video(chat_id, video=video)
        if video_note:
            await bot.send_video_note(chat_id, video_note=video_note)
        if audio:
            await bot.send_audio(chat_id, audio=audio)
        if image:
            await bot.send_photo(chat_id, photo=image)
    except Exception as e:
        logging.error(f"Failed to send message after delay: {e}")


@dp.message(CommandStart())
async def first_lesson(message: Message) -> None:
    try:
        user_states[message.from_user.id] = 'first_lesson'
        first_video = FSInputFile('teasers/first_teaser.mp4')
        await bot.send_video(
            chat_id=message.chat.id,
            video=first_video,
            width=720, height=405
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"Hey you, what's up {message.from_user.first_name}👋🏻\n\n"
                 f"🕸️Man Spiderman - Jahongir Saylavov sun'iy yordamchilari bo'laman😎\n\n"
                 f"Grammatikasiz speaking chiqarishni isbotlab beradigan DARSLIK shu yerda 👇🏻 \n\n"
                 f"📌Eslatib o'taman, darslik 24 soatdan keyin o'chib ketadi🫡\n",
            reply_markup=first_lesson_keyboard.as_markup()
        )

        await asyncio.create_task(
            send_message_after_delay(
                chat_id=message.chat.id,
                delay_minutes=.5,
                message="🫢1 soat ichida darslikni ko'rgan obunachilarimga, "
                        "BONUS sifatida yana bitta darslik sovg'a qilmoqchiman🎁\n\n"
                        "Shustriy bo'lsez, ulgurib qolasiz✊🏻",
                reply_markup=first_lesson_keyboard.as_markup()
            )
        )

        video_note_file = FSInputFile('circle_videos/teaser_one.mp4')
        await asyncio.create_task(
            send_message_after_delay(
                chat_id=message.chat.id,
                delay_minutes=.5,
                video_note=video_note_file
            )
        )

        await asyncio.create_task(
            send_message_after_delay(
                chat_id=message.chat.id,
                delay_minutes=.5,
                message=f"🗣️Hey you, do'stim yaxshimisiz ?\n\n"
                        f"🧠Sizga va'da qilgan darsimdan keyin "
                        f"SPEAKING haqidagi fikrlariz aniq o'zgargan bo'lsa kerak, to'g'rimi ?\n\n"
                        f"Darsni ko'rib bo'lganlarga 2-BONUS dars sovg'a qilmoqchiman🎁\n\n"
                        f"Darsni ko'rdizmi, bro ?",
                reply_markup=fr_reminder_keyboard.as_markup()
            )
        )

    except Exception as e:
        logging.error(f"Failed to send start message: {e}")


@dp.callback_query(F.data == 'watch_first_lesson')
async def watch_first_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'watch_first_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'watch_first_lesson'

    await query.message.reply(
        text=f"Hey, {query.from_user.first_name}\n\n"
             f"🗣️Agar siz haliyam ZO'R SPEAKING uchun GRAMMATIKA YODLASH kerak deb o'ylasez,\n\n"
             f"bepul darslikdan keyin aniq fikriz o'zgaradi💯\n\n"
             f"*Videodars 24 soatdan keyin o'chadi, tezroq ko'rishni maslahat beraman 🫡",
        reply_markup=first_lesson_keyboard.as_markup()
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.5,
            message=f"Hey, {query.from_user.first_name}👋🏻\n\n"
                    f"🧠 Bepul darsni allaqachon yuzlab til o'rganuvchilari ko'rib bo'lib, "
                    f"SPEAKING haqida fikrlarini o'zgartirishdi.💡\n\n"
                    f"Haliyam darsni ko'rmagan bo'lsez, hoziroq ko'rishni maslahat beraman🫡",
            reply_markup=first_lesson_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.5,
            message="🤯Grammatika yodlash jonimga tegdi?\n"
                    "🙍🏻Nega mani speakingim o'smas ekanaa?\n"
                    "🥲Balki ingliz tilini umuman o'rganolmasman..\n\n"
                    "🗣️Shunaqa fiklar bilan yashashdan charchab kettiz, to'g'rimi?\n\n"
                    "🫡Keling, man sizga yordam beraman. Siz uchun tekinga dars o'tib beraman.🎁\n\n"
                    "👇🏻Pastdagi tugmani bosib, bepul darsni ko'rib olishiz mumkin!",
            reply_markup=first_lesson_keyboard.as_markup()
        )
    )

    audio = FSInputFile('audio_2024-07-24_05-23-07.ogg')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.5,
            audio=audio
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.5,
            message=f"Sizga YOMON XABAR bor 🫢\n\n"
                    f"Bilaman, ishlar bilan bo'lib, darsni ko'rishga vaqt topolmagan bo'lishiz mumkin🙍🏻\n\n"
                    f"🇺🇸Lekin sizda ingliz tilini OSON va QIZIQARLI o'rganishingiz uchun\n\n"
                    f"12 soat vaqt bor ❗️\n\n"
                    f"📌Keyin, $*000 pul to'lasangiz ham bu darsni ololmaysiz!",
            reply_markup=first_lesson_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.5,
            message=f"Dars o'chib ketishiga 4 SOAT VAQT qoldi❗️\n\n"
                    f"🔝Shaxsiy rivojlanishiz uchun 10 minut vaqtizni o'zizdan qizg'onasizmi ❓\n\n"
                    f"😇Manimcha, yo'q ! \n\n"
                    f"Unda tezroq darsni ko'rib oling, manfaatli bo'ladi nasib..",
            reply_markup=first_lesson_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'second_lesson')
async def second_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'second_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'second_lesson'

    first_video = FSInputFile('teasers/second_teaser.mp4')
    await bot.send_video(
        chat_id=query.message.chat.id,
        video=first_video,
    )

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Eee malades, {query.from_user.first_name}\n\n"
             f"Endi sizda 2-darsni ko'rish imkoniyati bor 🎁\n\n"
             f"Bu darslikda : \n\n"
             f"❗️Speaking chiqarolmaslik sabablari va yechimlari\n"
             f"❗️Bir xil qolipdagi texnikalardan qutulib, QIZIQARLI yo'lda speaking o'rganish\n"
             f"❗️Qanday qilib man bir o'zim o'rganib, amerikanlardek speaking chiqarganim haqida o'rganasiz🫡\n"
             f"🗣️Sizda darslikni ko'rish uchun 24 soat vaqt bor. Shuning uchun, tezroq ko'ring✊🏻",
        reply_markup=second_lesson_keyboard.as_markup()
    )

    video_note_file = FSInputFile('circle_videos/teaser_two.mp4')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            video_note=video_note_file
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey, {query.from_user.first_name}!\n\n"
                    f"Bonus darslik sizga yoqtimi ?\n\n"
                    f"🗣️Ayniqsa, grammatikasiz speaking chiqarish degan joyiga  mazza qigandursizaa 😅 \n\n"
                    f"Agar darsni oxirgacha ko'rgan bo'lsez, sizga yana bitta dars mandan 🎁\n\n",
            reply_markup=sr_reminder_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'watch_second_lesson')
async def watch_second_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'watch_second_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'watch_second_lesson'

    await query.message.reply(
        text=f"🫣{query.from_user.first_name}, Ingliz tilida grammatika yodlashdan charchagan bo'lsez kerak a... \n\n"
             f"Qiziqarli va oson metodikada SPEAKING chiqarishga qanaqa qarisiz 🤔\n\n"
             f"🎁Bu haqida BONUS DARSLIKda tushuntirdim. \n\n"
             f"🤫Hoziroq ko'rsangiz, yana bitta darsga dostup olasiz❗️",
        reply_markup=second_lesson_keyboard.as_markup()
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Keling, biroz hisob-kitob qilamiz.. \n\n"
                    f"🗣️Odatiy yo'l bilan ingliz tili o'rgansangiz, 12 oydan 24  oygacha bo'lgan vaqtda yaxshi gapirasiz.\n\n"
                    f"🔝Mani metodikam bilan ingliz tili o'rgansangiz, 3 oydan 6 oygacha bo'lgan vaqtda bemalol ravon gapirolasiz!\n\n"
                    f"🤯QANDAY QILIB ? - deyabsizmi ?\n\n"
                    f"Bu haqida bepul darslikda tushuntirib berdim🎁\n\n"
                    f"Hoziroq darsni ko'rish uchun, pastdagi tugmani bosing👇🏻",
            reply_markup=sr_reminder_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Heey, {query.from_user.first_name}\n\n"
                    f"🫣Haliyam videoni ko'rmabsizaa, nimasi bu ?\n\n"
                    f"🇺🇸Bunaqada HAYOTIY ingliz tilini OSON o'rganish metodikasizdan quruq qolishiz aniq, bro🥲\n\n"
                    f"12 soatdan keyin darslikka DOSTUP YOPILADI ❗️\n\n"
                    f"Tezroq ko'rishga ulguring!",
            reply_markup=sr_reminder_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Sizga zo'r xabar bor, bro ✊🏻\n\n"
                    f"✅ 4 soat ichida GRAMMATIKASIZ SPEAKING darsligimni ko'rsangiz, sizga yana bitta darsni bepulga beraman🎁\n\n"
                    f"Faqat darsni ko'rib, o'zizga foyda olsez bo'ldi🫡\n\n",
            reply_markup=sr_reminder_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'third_lesson')
async def third_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'third_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'third_lesson'

    first_video = FSInputFile('teasers/second_teaser.mp4')
    await bot.send_video(
        chat_id=query.message.chat.id,
        video=first_video,
        width=720, height=405
    )

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Bu videoni yolg'iz ko'ring🤫\n\n"
             f"🇺🇸Sababi man bu videoda ingliz tilini HAYOT TARZIGA aylantirib, bosh og'riqlarsiz MULOQOT QILISH uchun \n\n"
             f"KUN TARTIBIM bilan bo'lishganman🔥 \n\n"
             f"Diqqatizni bir joyga qo'yib, videoni ko'ring va berilgan maslahatlardan mazza qilib foydalaning ✅",
        reply_markup=third_lesson_keyboard.as_markup()
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"💭Shunaqa qilib grammatika yodlamay, ingliz tilini hayot tarzimga aylantirib ham o'rganib olsam bo'larkanda... \n\n"
                    f"🫢Agar darsni ko'rgan bo'lsez, sizda ham shunday fikr o'tgan bo'lsa kerak.\n\n"
                    f"Xo'sh, sizga so'ngi videoda AJOYIB TAKLIF bermoqchiman🎁\n\n"
                    f"Darsni ko'rdizmi ?",
            reply_markup=tr_reminder_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'watch_third_lesson')
async def watch_third_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'watch_third_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'watch_third_lesson'

    await query.message.reply(
        text=f"🗣️Ingliz tilida SPEAKING qilish sizda muommo bo'lmaydi❗️\n\n"
             f"Agar siz bu darsni ko'rib, berilgan KUN TARTIBIGA amal qilsangiz🔥\n\n"
             f"Darsni ko'rish uchun pastdagi tugmani bosing👇🏻\n\n",
        reply_markup=third_lesson_keyboard.as_markup()
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Agar siz haliyam ingliz tili o'rganish uchun 2-4 soat vaqt ajratsangiz, demak juda qiyin usuldan foydalanyapsiz❗️\n\n"
                    f"🗣️Keling, man sizga ham OSON, ham QIZIQARLI metodika o'rgataman🎁\n\n"
                    f"Keyin siz ingliz tili muhitini yaratib, 3 oyda ravon gapira olasiz✅\n\n"
                    f"Darslikda hammasini tushuntirib berdim👇🏻\n\n",
            reply_markup=tr_reminder_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Afsuski, sizga bir xabar yetkazmoqchiman❗️\n\n"
                    f"12 soatdan keyin video o'chib ketarkan, shuning uchun darsni tezroq ko'rib olishni maslahat beraman, bro🎁\n\n"
                    f"🔝Man bergan METODIKA va KUN TARTIBNI boshqa joydan topa olmisiz, deb qo'rqaman🫢\n\n"
                    f"Darsni ko'rish uchun tugmani bosing👇🏻\n\n",
            reply_markup=tr_reminder_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey, {query.from_user.first_name}\n"
                    f"Sizga oxirgi marta eslatib qo'yay dedim ☺️\n\n"
                    f"4 soatdan keyin BEPUL DARSLIK o'chib ketadi va siz boshqa bu darslikni pul to'lab ham ololmaysiz ❗️\n\n"
                    f"Shuning uchun, darsni hozir ko'rib, mazza qilib ingliz tilida gapirish formulasini olishingizni tavsiya qilaman✅\n\n"
                    f"Sog' bo'ling 👋🏻",
            reply_markup=tr_reminder_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'fourth_lesson')
async def fourth_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'fourth_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'fourth_lesson'

    first_video = FSInputFile('teasers/fourth_teaser.mp4')
    await bot.send_video(
        chat_id=query.message.chat.id,
        video=first_video,
        width=720, height=405
    )

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Hey you, {query.from_user.first_name}\n"
             f"CONGRATULATIONS🥳\n\n"
             f"Oxirgi darsga yetib kelganiz bilan sizi tabrikliman ! \n\n"
             f"Bilasizmi, siz ancha intizomli va harakatchan til o'rganuvchisi ekansiz🔥\n\n"
             f"Chunki hammayam yangi til o'rganishi uchun e'tibor qilmaydi.\n\n"
             f"🔝Shuning uchun, sizga to'g'ri keladigan va yoqadigan TAKLIF tayyorlab qo'yganman🤝🏻\n\n"
             f"Bu haqida videoda bilib olasiz👇🏻",
        reply_markup=fourth_lesson_keyboard.as_markup()
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"👋🏻Hey what's up, {query.from_user.first_name}\n"
                    f"Sizga bergan videoimni ko'rdizmi ? \n\n"
                    f"Ko'rgan bo'lsangiz, manimcha sizga bergan taklifim aniq yoqdi🔥 \n\n"
                    f"🇺🇸Kurs haqida to'liq ma'lumot uchun sizga havola berishimni xohlisizmi ? ",
            reply_markup=for_reminder_keyboard.as_markup()
        )
    )


@dp.callback_query(F.data == 'watch_fourth_lesson')
async def watch_fourth_lesson(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'watch_fourth_lesson':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'watch_fourth_lesson'

    await query.message.reply(
        text=f"Bilasizmi, {query.from_user.first_name}\n\n"
             f"📌Bu video hammasidan ham muhim, chunki bu videodan keyin siz \n\n"
             f"Hayotingizda katta qaror qabul qilasiz❗️\n\n"
             f"- Yoki ingliz tili o'rganishni boshlaysiz va rivojlanasiz\n"
             f"- Yoki videoni ko'rmay, bir xil holatda qolib ketasiz\n\n"
             f"Eng yomoni ingliz tilini samarasiz metodikalarda o'rganishni davom etib, yillab vaqtingizu millionlab pullarizni bekorga sarf qivorasiz...\n\n"
             f"Tanlov o'zizda, shustri bo'ling 😉",
        reply_markup=for_reminder_keyboard.as_markup()
    )

    video_note_file = FSInputFile('circle_videos/teaser_four.mp4.mp4')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            video_note=video_note_file
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"'JUST SPEAK' kursim nega qo'rqmasdan O'zbekistonda yagona deyman ? \n\n"
                    f"1. Mani shaxsiy grammatikasiz speaking chiqarish metodikam boshqa ustozlarda yo'q ! \n\n"
                    f"2. Ingliz tili darajezdan qat'iy nazar, bu kurs sizga to'g'ri keladi. Chunki kursda hayotiy speaking ustida ishlaymiz.\n\n"
                    f"3. Faqat mani kursimda Kino ko'rib, musiqa eshitib ingliz tilida gaplashishni o'rganasiz. \n\n"
                    f"Agar siz ham JUST SPEAK oilamizga qo'shilib, ingliz tilida ravon gaplashishni xohlasangiz,\n\n"
                    f"pastdagi ANKETAni to'ldiring👇🏻",
            reply_markup=for_reminder_keyboard.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey you, what's up ? 👋🏻\n\n"
                    f"Agarda siz kursimga anketa to'ldirib, ro'yhatdan o'tgan bo'lsangiz,\n\n"
                    f"lekin sizga hali aloqacha chiqishmagan bo'lsa,\n\n"
                    f"Adminga yozib, kursga qo'shilishingiz mumkin🫡\n\n"
                    f"@JahongirPrankAdmin",
            reply_markup=admin.as_markup()
        )
    )

    first_student = FSInputFile('pictures/student.jpg')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            image=first_student
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.01,
            message=f"Keling, sizga monster o'quvchilarimdan ba'zilarini tanishtiraman😉\n\n"
                    f"O'quvchim Jaloliddin, 16 yoshda.\n\n"
                    f"Manga kelganda grammatikani ozgina bilardiyu, gapirolmasdi.\n\n"
                    f"🗣️6 oy birga shug'illandik va hozir bemalol ingliz tilida gapiradi, tushunadi, real hayotda ishlatoladi.\n\n"
                    f"Hozir, ko'z tegmasin, IT sohasida ishlaydi va hayotda o'z yo'lini topgan. 🙌🏻\n\n"
                    f"📌Agar siz ham O'quvchilarimga o'xshab ingliz tili orqali hayotizni o'zgartirishni xohlasez,\n\n"
                    f"ANKETAni albatta to'ldiring❗️",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"💭Tasavvur qiling, siz haqiqiy inglizlardek gapirolasiz🥹\n\n"
                    f"🇺🇸Hattoki ingliz tilida gapirayotganizniyam sezmay qolasiz😇\n\n"
                    f"Bu xomhayol emas ❗️\n\n"
                    f" 3 oylik JUST SPEAK online kursi bilan buni iloji  bor🔥\n\n"
                    f"Ro'yhatdan o'tish uchun quyidagi ANKETAni to'ldiring👇🏻\n\n",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"🫵🏻Bu xabarni ko'rgan bo'lsez, demak siz omadlisiz🏆\n\n"
                    f"🚀Ingliz tilida amerikanlardek gapirishingiz uchun 3 oy yetarli🫢 \n\n"
                    f"🔥Hamma so'ragan online Speaking kursiga qo'shiling va 3 oydan keyin inglizlardek gapiring😎\n\n"
                    f"Kursga qo'shilish uchun ANKETAni to'ldiring, biz  sizga bog'alanamiz😇",
            reply_markup=google_form_k.as_markup()
        )
    )

    second_student = FSInputFile('pictures/student2.jpg')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            image=second_student
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.01,
            message=f"Kursda o'qigandan keyin qanday natija olishizi bir tushuntirib beray..\n\n"
                    f"🙋🏻‍♂️Masalan, o'quvchim Ibrohim.\n\n"
                    f"❗️U mani oldimga keganda hattoki grammatikani bilmasdi, gapirish uyoqda tursin. \n\n"
                    f"1 yil ichida o'zim noldan tarbiyaladim dsamam bo'ladi✊🏻\n\n"
                    f"✅Hozir daje ingliz tilida gapirvotganini sezmidi, kino ko'rsa yoki musiqa eshitsa beemalol tushunadi.\n\n"
                    f"Agar siz ham shunday natijaga chiqishni xohlasez, ANKETAni to'ldiring👇🏻",
            reply_markup=google_form_k.as_markup()
        )
    )

    video_note_file = FSInputFile('circle_videos/student3.mp4')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            video_note=video_note_file
        )
    )

    third_student = FSInputFile('pictures/student3.jpg')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            image=third_student
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=.01,
            message=f"Yoki o'quvchim Madina \n\n"
                    f"☹️Oldin grammatika o'qib, gapirolmagani uchun mani oldimga kegandi.\n\n"
                    f"Biz u bilan 6 oy speaking va talaffuzi ustida ishladik. \n\n"
                    f"Natijada hozir beemalol amerikanlardek gaplasholadi va lyuboy kino qo'yibersez, 70% tushunib, tarjima qiliberoladi✅\n\n"
                    f"‼️Madinani fikrlarini tepadagi videoda eshitsez boladi✊🏻\n\n"
                    f"Siz ham shunday natijaga erishishni xohlasangiz, hoziroq ANKETANI TO'LDIRING !",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey, {query.from_user.first_name} what's up !\n\n"
                    f"Sizga muhim xabarim bor❗️\n\n"
                    f"🗣️3 oylik JUST SPEAK kursimda qo'shilish uchun vaqt kam oldi....\n\n"
                    f"Shu bilan bu kurs yana 4 oydan keyin bo'ladi.\n\n"
                    f"Agar hozir kursga qo'shilishga ulgursangiz, 3 oydan keyin mazza qilib ingliz tilida gapirayotgan bo'lasiz😍\n\n"
                    f"📌Tanlov o'zizda !",
            reply_markup=google_form_k.as_markup()
        )
    )

    video_note_file = FSInputFile('circle_videos/teaser_four2.mp4')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            video_note=video_note_file
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey {query.from_user.first_name}, siz bir narsani o'ylab ko'rishiz kerak❗️ \n\n"
                    f"Agar istalgan o'quv markazga borsez, 12 ta darsni kamida 500 minga sotib olasiz. O'quv markazda bitta darajani 3 oy o'qiysiz."
                    f" Speakingni zo'r chiqaraman deguncha, 6-8 oy vaqt va millionlab pul ketkizvorasiz. \n\n"
                    f"🔝Mani kursim 3 oy davom etishi va 100 dan ko'p darslar borligini inobatga olib qo'yishingiz kerak🫡 \n\n"
                    f"Boshizni og'ritmasdan, ingliz tili atmasferasini yaratib mazza qilib ingliz tili o'rganmisizmi ey, shustri bollaga o'xshab😎 \n\n"
                    f"Shustriy o'quvchilarim qatoriga qo'shilishi xohlasangiz, ANKETANI to'ldiring😉\n\n"
                    f"JOYLAR KAM QOLDI ❗️",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey you, what's up ? 👋🏻\n\n"
                    f"Agarda siz kursimga anketa to'ldirib, ro'yhatdan o'tgan bo'lsangiz,\n\n"
                    f"lekin sizga hali aloqacha chiqishmagan bo'lsa,\n\n"
                    f"Adminga yozib, kursga qo'shilishingiz mumkin🫡\n\n"
                    f"@JahongirPrankAdmin",
            reply_markup=admin.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Bilasizmi, {query.from_user.first_name}\n\n"
                    f"Agar sizga ingliz tilini o'rganish qiziq bo'lsa, "
                    f"hayotizni o'zgartirishni xohlasangiz,\n\n"
                    f"SHOSHILISHINGIZ KERAK ❗️\n\n"
                    f"Chunki 3 oylik speaking kursimga qa'bul yopishiga oz qoldi 🤝🏻\n\n"
                    f"Keyin, bu kursga yozilolmay qolishiz mumkin.\n\n"
                    f"Shuning uchun, hoziroq ANKETANI TO'LDIRING 👇🏻",
            reply_markup=google_form_k.as_markup()
        )
    )

    image = FSInputFile('pictures/adver.jpg')
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            image=image
        )
    )
    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=0.01,
            message=f"Jahongir bro, o'zi darsni qanday o'tasiz deb o'ylasez,\n\n"
                    f"rasmdagi fikrlarni o'qib ko'ring😉\n\n"
                    f"Agar siz ham mani o'quvchilarim bilan mazza qilib ingliz tiliga gapirishni xohlasangiz,\n\n"
                    f"3 oylik online kursim aynan siz uchun 🔥\n\n"
                    f"Kursga qo'shilish uchun anketani to'ldiring 👇🏻",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"🫢 6 oyda bir beriladigan imkoniyatni sizga so'ngi marta bermoqchiman🔥\n\n"
                    f"3 oylik online JUST SPEAK kursimga qo'shilish uchun sizda oxirgi imkoniyat bor ❗️"
                    f"O'zingiz va bilimingiz uchun 2 daqiqa vaqt ajratib, ANKETAni to'ldiring 👇🏻\n\n"
                    f"Sizga managerlarim aloqaga chiqishadi🤝🏻",
            reply_markup=google_form_k.as_markup()
        )
    )

    await asyncio.create_task(
        send_message_after_delay(
            chat_id=query.message.chat.id,
            delay_minutes=1,
            message=f"Hey you, what's up ? 👋🏻\n\n"
                    f"Agarda siz kursimga anketa to'ldirib, ro'yhatdan o'tgan bo'lsangiz,\n\n"
                    f"lekin sizga hali aloqacha chiqishmagan bo'lsa,\n\n"
                    f"Adminga yozib, kursga qo'shilishingiz mumkin🫡\n\n"
                    f"@JahongirPrankAdmin",
            reply_markup=admin.as_markup()
        )
    )


@dp.callback_query(F.data == 'google_form')
async def google_form(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if user_states.get(user_id) == 'google_form':
        await query.answer("You have already selected an option.")
        return

    user_states[user_id] = 'google_form'

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"🔥 DIQQAT, men  hozir sizga  JUST SPEAK kursimga yozilish uchun dostup beraman✅\n\n"
             f"• Online kurs 3 oy davom etadi.\n"
             f"• Darajangizni farqi yo'q, speaking 0 dan ravon gapirishgacha darslar bo'ladi.\n"
             f"• Uyga vazifalar va mentorlar nazorati bor.\n\n"
             f"🤝🏻So'rovnomani to'ldiring va sizga managerlar aloqaga chiqib to'liq ma'lumot berishadi👇🏻\n\n"
             f"https://forms.gle/6HCyDD4QBwqrXWNF8"
    )


async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Polling failed: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
