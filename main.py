import logging
import shutil
import urllib.request
from fpdf import FPDF
import PIL
import requests
import json
import os
from os import listdir
from os.path import isfile, join
from telegram import Update, ForceReply, user
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from tokenauth import TOKEN_API

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

class Book:
    def __init__(self, book_url, userid):
        self.base_url = 'https://digi.vatlib.it/'
        self.validated = self.validate_link(book_url)
        if self.validated is None:
            return
        else:
            self.temp_path = self.make_temp_path(userid)
            self.url = book_url
            self.data = self.get_json_details()
            self.label = self.data['label']
            self.imgs_path = self.make_book_temp_path()
        
    

    def validate_link(self, text):
        if not self.base_url in text:
            return None
        
        if ' ' in text:
            splitted = text.split(' ')
            for portion in splitted:
                if self.base_url in portion:
                    return portion
        else:
            return text

    def make_img_path(self, index, book_img_path):
        cifre = len(str(index))
        if cifre == 1:
            file = "000" + str(index) + ".jpeg"
        elif cifre == 2:
            file = "00" + str(index) + ".jpeg"
        elif cifre == 3:
            file = "0" + str(index) + ".jpeg"
        else:
            file = str(index) + ".jpeg"

        img_path = os.path.join(book_img_path, file)
        return img_path

    def get_link_list(self):
        canvases = self.data['sequences'][0]['canvases']
        download_uri = "/full/full/0/native.jpg"
        download_list = []
        for canvas in canvases:
            image_id = canvas['images'][0]['resource']['service']['@id']
            download_link = image_id + download_uri
            download_list.append(download_link)
        return download_list

    def make_temp_path(self, userid):
        temp_path = os.path.join(f'temp-{userid}')
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        return temp_path

    def make_book_temp_path(self):
        bookpath = os.path.join(self.temp_path, f"{self.label}")
        if not os.path.exists(bookpath):
            os.makedirs(bookpath)
        return bookpath

    def makePdf(self, pdfpath):
        Pages = [f for f in listdir(self.imgs_path) if isfile(join(self.imgs_path, f))]
        if Pages:
            pdfpdf_file_path = os.path.join(pdfpath, f"{self.label}.pdf")

            coverimage = os.path.join(self.imgs_path, Pages[0])
            cover = Image.open(coverimage)
            width, height = cover.size

            pdf = FPDF(unit="pt", format=[width, height])

            for page in Pages:
                pdf.add_page()
                pdf.image(os.path.join(self.imgs_path, page), 0, 0)

            pdf.output(pdfpdf_file_path, "F")

    def get_json_details(self):
        base_url = 'https://digi.vatlib.it/'
        book_id = self.url.split("/")[-1:][0]
        manifest_url = base_url + "iiif/" + book_id + "/manifest.json"

        r = requests.get(manifest_url)
        data = json.loads(r.text)
        return data


    def download_image(self, url, img_path):
        urllib.request.urlretrieve(url, img_path)

    def download_book(self, list):
        for index, url in enumerate(list):
            img_path = self.make_img_path(index, self.imgs_path)
            self.download_image(url, img_path)


    def start_download(self, link_list, label):
        self.download_book(link_list)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\!\n Send me a link to download a book.',
        reply_markup=ForceReply(selective=True),
    )


def info_command(update: Update, context: CallbackContext) -> None:
    message_content = 'This is a bot created to download books in PDF format from the Digital Vatican Library website: https://digi.vatlib.it/\n'\
        'Just send a link and if it is valid the bot will convert the book in pdf format and send it to you.\n'\
            'If the bot stops working please send a message to @litiasi'
    update.message.reply_text(message_content)


def process_link_command(update: Update, context: CallbackContext) -> None:
    book = Book(update.message.text, str(update.message.from_user.id))
    validated = book.validate_link()
    if validated is None:
        update.message.reply_text('The message does not contain any valid link.')
        return None
    update.message.reply_text('Trying to process your request, please wait for a confirmation message.')
    try:
        link_list = book.get_link_list()
        book.start_download(link_list, book.label)

        pdfpath = os.path.join(f"PDF-{str(update.message.from_user.id)}")
        if not os.path.exists(pdfpath):
            os.makedirs(pdfpath)

        book.makePdf(pdfpath)
        file = os.path.join(pdfpath, f"{book.label}.pdf")

        update.message.reply_document(document=open(file, 'rb'), filename=f"{book.label}.pdf")
        shutil.rmtree(book.temp_path)
        shutil.rmtree(pdfpath)

    except:
        update.message.reply_text('For some reason i could not download the book you requested.')
    



def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN_API)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("info", info_command))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_link_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()