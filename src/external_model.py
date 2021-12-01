import openai
import os
import time
import twee_utils as utils

openai.api_key = os.getenv("OPENAI_KEY")
ZERO_SHOT = open('src/zero_shot.txt', 'r').read()


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
    def summarize(passage, clean_passage=True):
        """
        Use GPT-3 as a zero-shot summarization for the given passage.

        :param clean_passage: (bool) whether to clean the passage of extraneous twee formatting
        """

        if clean_passage:
            passage = utils.passage_to_text(passage)
        prompt = ZERO_SHOT.format(passage.strip())
        model = 'davinci'  # It doesn't really work with curie
        response = openai.Completion.create(
            model=model,
            prompt=prompt,
            temperature=0.7,
            max_tokens=280,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop='.',
        )

        response = response['choices'][0]['text']
        return response.strip() + '.'

    @staticmethod
    def _mock_generate(prompt):
        time.sleep(1)
        result = {}
        result['completion'] = \
            """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|dotdotdot]]<|end|>"""
        return result

# Usage: python src/external_model.py
if __name__ == '__main__':
    mem = "This happened sometime ago now, but I still treasure this memory close to my heart. I've always wanted to execute the perfect date for a girl, and that day would come when I met my Loretta. One night, I really wanted to do something romantic for her. I'm twenty two but my ideas are rather old fashioned. I decided a surprise picnic would be a perfect date for Loretta. I thought she'd love it. I ended up secretly buying all her favorite foods I could think of, creating a playlist of all our favorite love songs, and packing her favorite blankets. Everything was going to plan. Well, until the day I decided to actually put my plan into motion. On the day of the picnic, I finally realized the one thing I forgot to do while planning this picnic, check the weather. It ended up pouring down hard that day. However, that didn't stop my plans. Instead of feeling defeated and calling it a night I decided to execute a quick plan B. I had brought Loretta to my room, and I began to set the stage. With the lights dimmed and a fake fireplace roaring on my tv, I turned on my blue tooth speaker and prepared the playlist I made. I had set up the blankets and cups, along with everything else I had ready for the picnic, and had everything laid out nicely on the clear floor. Loretta was overjoyed that I had gone through all this trouble for her. After we ate she snuggled up with me as we kissed and let the music play until it's end. We're still happily together and of course now I always remember to check the weather, but Loretta still says that night was very special to her, and it is to me as well! "
    ex = "She was gorgeous and I was in love with her. When we made out for the first time, the world came to a halt. It literally blew up. No one survived, except for us."
    sum = TwineGenerator.summarize(ex, False)
    print('summary: ', sum)