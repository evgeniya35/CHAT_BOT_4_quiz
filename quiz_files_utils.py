import os
import re


def make_questions_answers(folder):
    folder = os.path.join(os.path.dirname(__file__), folder)
    all_questions_answers = {}
    for filename in os.listdir(folder):
        with open(os.path.join(folder, filename), 'rt', encoding='KOI8-R') as file:
            content = file.read().split('\n\n')
        questions = []
        answers = []
        for line in content:
            if line.startswith('Вопрос'):
                questions.append(' '.join(line.split('\n')[1:]))
            if line.startswith('Ответ'):
                answers.append(' '.join(line.split('\n')[1:]))
        questions_answers = dict(zip(questions, answers))
        all_questions_answers.update(questions_answers)
    return all_questions_answers


def multi_split(delimiters, string, maxsplit=0):
    regex_pattern = '|'.join(map(re.escape, delimiters))
    return re.split(regex_pattern, string, maxsplit)
