import openai
import os
import time

openai.api_key = os.getenv("OPENAI_KEY")
from src import twee_utils as utils


def call_finetuned_completion_model(prompt):
    """
    Return a generated twee passge from a given title. The code is elsewhere modular to allow this to be re-implemented
    with any language model. Here, we call a fine-tuned GPT-3 instance trained to generate scaffolded Twee.
    """

    model = 'curie:ft-user-wmco7qacght9seweh8jgp4ib-2021-10-28-04-55-18'

    response = openai.Completion.create(
        model=model,
        prompt=prompt,
        temperature=0.7,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=utils.END,
    )

    return response['choices'][0]['text']


def mock_generate(prompt):
    time.sleep(1)
    result = {}
    result['completion'] = \
        """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|dotdotdot]]<|end|>"""
    return result


# Decide which generator to use (GPT-3 or mock)
get_completion = call_finetuned_completion_model
