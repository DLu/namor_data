import unicodedata
from unidecode import unidecode

LETTER_ALPHABETS = ['LATIN']
CHUNKS = ['NO', 'QR', 'UVW', 'XYZ']
REMAP_ALPHABET = {}
for chunk in CHUNKS:
    for letter in chunk:
        REMAP_ALPHABET[letter] = chunk
FULL_ALPHABETS = ['CYRILLIC', 'HIRAGANA', 'GREEK', 'ARABIC', 'ARMENIAN', 'BENGALI', 'HEBREW']


def get_alphabet(category_name):
    words = category_name.split()
    for splitter in ['LETTER', 'SYLLABLE', 'CHARACTER', 'SIGN', 'SYLLABICS']:
        if splitter not in words:
            continue
        i = words.index(splitter)
        if splitter == 'LETTER' and i > 0 and words[i - 1] in ['CAPITAL', 'SMALL', 'CURSIVE']:
            i -= 1
        return ' '.join(words[:i])


def get_ascii_letter(letter):
    translated = unidecode(letter).upper()
    if len(translated) > 1:
        translated = translated[0]
    if translated.isalpha():
        return translated


def get_bucket(s):
    letter = s[0]
    cat = unicodedata.category(letter)
    if cat[0] != 'L':
        return 'Other',

    try:
        category_name = unicodedata.name(letter)
    except KeyError:
        return 'Other',

    if category_name.startswith('CJK'):
        return 'CJK',

    alphabet = get_alphabet(category_name)

    if alphabet in LETTER_ALPHABETS:
        ascii = get_ascii_letter(letter)
        if not ascii:
            ascii = 'Other'
        else:
            ascii = REMAP_ALPHABET.get(ascii, ascii)
        return alphabet.title(), ascii
    elif alphabet in FULL_ALPHABETS:
        return alphabet.title(),
    else:
        return 'OtherLetter',
