import os
import pathlib
import textwrap

import google.generativeai as genai



from IPython.display import display
from IPython.display import Markdown


def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

# Your Gemini API key and Settings
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(
    api_key=GEMINI_API_KEY
)

for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)