import openai
import os
import time
import twee_utils as utils

openai.api_key = os.getenv("OPENAI_KEY")


class TwineGenerator:
    def __init__(self, model='context', verbose=True):
        """
        :param model: must be one of: 'context', 'mock', or 'naive'
            context: Call GPT-3 with a context description and passage title
            naive: Call GPT-3 with only a passage title
            mock: Mock the language model call

        Each will return a passage body that can be appended to the title to make a complete Twee passage.
        """
        # Decide which generator to use (GPT-3 or mock)
        model = model.lower()
        self.verbose = bool(verbose)
        if model == 'context':
            self.call_model = TwineGenerator._call_contextual_model
        elif model == 'mock':
            self.call_model = TwineGenerator._mock_generate
        else:
            self.call_model = TwineGenerator._call_naive_model

    def get_completion(self, prompt):
        """
        call the correct language model
        """
        if self.verbose:
            print("prompt", prompt)

        while True:
            try:
                return self.call_model(prompt)
            except openai.error.RateLimitError as e:
                print(e)
                print('retrying...')

    def call_model(self, prompt):
        raise RuntimeError("This should have been defined in the constructor")

    @staticmethod
    def _call_naive_model(prompt):
        """
        Return a generated twee passage from a given title. The code is elsewhere modular to allow this to be re-implemented
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

    @staticmethod
    def _call_contextual_model(prompt):
        """
        Return a generated twee passage from a given title. The code is elsewhere modular to allow this to be re-implemented
        with any language model. Here, we call a fine-tuned GPT-3 instance trained to generate scaffolded Twee.
        """

        model = 'curie:ft-user-wmco7qacght9seweh8jgp4ib-2021-11-29-05-45-10'

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

    @staticmethod
    def _mock_generate(prompt):
        time.sleep(1)
        result = {}
        result['completion'] = \
            """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|dotdotdot]]<|end|>"""
        return result
