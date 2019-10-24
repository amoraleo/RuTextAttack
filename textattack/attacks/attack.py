# @TODO all files should have some copyright header or something

"""" @TODOs:
    - Example of using with Pytorch and Tensorflow model.
    - sphinx documentation
    - add recipes with state-of-the-art attacks
    - add unit tests
    - add pep8 standard
    - upload sample models and datasets
    - add logger... we should never call print()
    - make it much quieter when we load pretrained BERT. It's so noisy right now :(
    - try to refer to 'text' not 'sentences' (better terminology)
    - make this into a pip package (not on pypi, just a local package)
"""

import difflib
import torch

from textattack import utils as utils
from textattack.tokenized_text import TokenizedText

class Attack:
    """ 
    An attack generates adversarial examples on text. 

    Args:
        model: A PyTorch NLP model
        perturbation: The type of perturbation

    """

    def __init__(self, model, perturbation):
        """ Initialize an attack object.
        
        Attacks can be run multiple times
        
         @TODO should `tokenizer` be an additional parameter or should
            we assume every model has a .tokenizer ?
        """
        self.model = model
        self.perturbation = perturbation
        # List of files to output to.
        self.output_files = []
        self.output_to_terminal = True
        self.output_to_visdom = False
    
    def add_output_file(self, file):
        """ 
        When attack runs, it will output to this file. 

        Args:
            file (str): The path to the output file
            
        """
        if isinstance(file, str):
            file = open(file, 'w')
        self.output_files.append(file)
    
    def _attack_one(self, label, tokenized_text):
        """ Perturbs `text` to until `self.model` gives a different label
            than `label`. """
        raise NotImplementedError()
    
    def _call_model(self, tokenized_text_list):
        """ Returns model predictions for a list of TokenizedText objects. """
        # @todo support models that take text instead of IDs.
        ids = torch.tensor([t.ids for t in tokenized_text_list])
        ids = ids.to(utils.get_device())
        return self.model(ids).squeeze()
    
    def attack(self, dataset, shuffle=False):
        """ 
        Runs an attack on the given dataset and outputs the results to the console and the output file.

        Args:
            dataset: An iterable of (label, text) pairs
            shuffle (:obj:`bool`, optional): Whether to shuffle the data. Defaults to False.

        Returns:
            The results of the attack on the dataset

        """
        if shuffle:
            random.shuffle(dataset)
        
        results = []
        for label, text in dataset:
            tokenized_text = TokenizedText(self.model, text)
            result = self._attack_one(label, tokenized_text)
            results.append(result)
        
        # @TODO Support failed attacks. Right now they'll throw an error
        
        if self.output_to_terminal:
            for i, result in enumerate(results):
                print('-'*35, 'Result', str(i+1), '-'*35)
                result.print_()
                print()
        
        if self.output_files:
            for output_file in self.output_files:
                for result in results:
                    output_file.write(str(result) + '\n')
        
        if self.output_to_visdom:
            # @TODO Support logging to Visdom.
            raise NotImplementedError()
        
        print('-'*80)
        
        return results

class AttackResult:
    """
    Result of an Attack run on a single (label, text_input) pair. 

    Args:
        original_text (str): The original text
        perturbed_text (str): The perturbed text resulting from the attack
        original_label (int): he classification label of the original text
        perturbed_label (int): The classification label of the perturbed text

    
    @TODO support attacks that fail (no perturbed label/text)
    """
    def __init__(self, original_text, perturbed_text, original_label,
        perturbed_label):
        self.original_text = original_text
        self.perturbed_text = perturbed_text
        self.original_label = original_label
        self.perturbed_label = perturbed_label
    
    def __data__(self):
        data = (self.original_text, self.original_label, self.perturbed_text,
                self.perturbed_label)
        return tuple(map(str, data))
    
    def __str__(self):
        return '\n'.join(self.__data__())
    
    def diff(self):
        """ 
        Highlights the difference between two texts using color.
        
        @TODO abstract to work for general paraphrase.
        """
        #@TODO: Support printing to HTML in some cases.
        _color = utils.color_text_terminal
        t1 = self.original_text
        t2 = self.perturbed_text
        
        words1 = t1.words()
        words2 = t2.words()
        
        c1 = utils.color_from_label(self.original_label)
        c2 = utils.color_from_label(self.perturbed_label)
        new_is = []
        new_w1s = []
        new_w2s = []
        for i in range(min(len(words1), len(words2))):
            w1 = words1[i]
            w2 = words2[i]
            if w1 != w2:
                new_is.append(i)
                new_w1s.append(_color(w1, c1))
                new_w2s.append(_color(w2, c2))
        
        t1 = self.original_text.replace_words_at_indices(new_is, new_w1s)
        t2 = self.original_text.replace_words_at_indices(new_is, new_w2s)
                
        return (str(t1), str(t2))
    
    def print_(self):
        print(str(self.original_label), '-->', str(self.perturbed_label))
        print('\n'.join(self.diff()))

if __name__ == '__main__':
    from . import attacks
    from . import constraints
    from .datasets import YelpSentiment
    from .models import BertForSentimentClassification
    from .perturbations import WordSwapCounterfit
    
    # @TODO: Running attack.py should parse args and run script-based attacks 
    #       (as opposed to code-based attacks)
    model = BertForSentimentClassification()
    
    perturbation = WordSwapCounterfit()
    
    perturbation.add_constraints((
        # constraints.syntax.LanguageTool(1),
        constraints.semantics.UniversalSentenceEncoder(0.9, metric='cosine'),
        )
    )
    
    attack = attacks.GreedyWordSwap(model, perturbation)
    
    yelp_data = YelpSentiment(n=2)
    # yelp_data = [
    #     (1, 'I hate this Restaurant!'), 
    #     (0, "Texas Jack's has amazing food.")
    # ]
    
    # attack.enable_visdom()
    attack.add_output_file(open('outputs/test.txt', 'w'))
    import sys
    attack.add_output_file(sys.stdout)
    
    attack.attack(yelp_data, shuffle=False)
