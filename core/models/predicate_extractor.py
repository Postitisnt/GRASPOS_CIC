from models.model_manager import ModelManager
from models.concept_extractor import ConceptExtractor as CE
import re

class PredicateExtractor(ModelManager):
	CORE_COMPONENT = [
		'prt',
		'neg', # negation
	]
	FELLOW_IDENTIFIER = [ # https://universaldependencies.org/u/dep/all.html
		'aux', # auxiliary
		'prep', # preposition
		'agent',
	]

	FELLOW_REGEXP = re.compile('|'.join(FELLOW_IDENTIFIER+CORE_COMPONENT))
	
	def __init__(self, model_options):
		self.min_concept_size = model_options.get('min_concept_size',2)
		super().__init__(model_options.get('tf_model', None))

	@staticmethod
	def is_passive(span): # return true if the sentence is passive - at he moment a sentence is assumed passive if it has an auxpass verb
		for token in span:
			if token.dep_ == "auxpass":
				return True
		return False

	@staticmethod
	def get_pattern_key(pattern):
		return '{0}.{1}.{2}.{3}'.format(pattern['predicate_core'].text, pattern['predicate_core'].idx, pattern['concept_core'].text, pattern['concept_core'].idx)

	@staticmethod
	def get_predicate_core(token):
		if token.pos_ == 'VERB':
			return token
		for token in token.ancestors:
			if token.pos_ == 'VERB':
				return token
		return None

	@staticmethod
	def get_composite_predicate_core(token):
		main_verb = PredicateExtractor.get_predicate_core(token)
		if main_verb is None:
			return None
		composite_predicate_core = [main_verb]
		for child in main_verb.children:
			#print(token, child, child.dep_)
			if child.dep_ in PredicateExtractor.CORE_COMPONENT:
				composite_predicate_core.append(child)
		composite_predicate_core.sort(key=lambda x: x.i)
		return composite_predicate_core

	def get_predicate(self, token):
		#token = self.get_concept_core(span)
		#if token is None:
		#	return None
		
		predicate_core = self.get_predicate_core(token)
		if predicate_core is None:
			return None

		#for child in predicate_core.children:
		#	print(child, CE.get_token_dependency(child))
		predicate = [
			child
			for child in predicate_core.children
			if re.search(self.FELLOW_REGEXP, CE.get_token_dependency(child))
		]
		predicate.append(predicate_core)
		predicate.sort(key=lambda x: x.i)#, reverse=False if 'subj' in token.dep_ else True)

		predicate_dict = { 
			'predicate': CE.get_concept_text(predicate),
			'predicate_span': predicate, 
			'predicate_core': predicate_core,
			'composite_predicate_core': self.get_composite_predicate_core(predicate_core),
			#'dependency': CE.get_token_dependency(token), 
			#'pid': predicate_core.i,
		}
		predicate_dict['composite_predicate_core_lemma'] = CE.lemmatize_span(predicate_dict['composite_predicate_core'], prevent_verb_lemmatization=False)
		return predicate_dict

	def get_pattern_from_concept(self, concept_dict):
		core_concept = concept_dict['core']
		predicate_dict = self.get_predicate(core_concept)
		if predicate_dict is None or len(predicate_dict['predicate']) == 0:
			return None
		if len(concept_dict['concept']) == 0:
			return None
		role_dict = {
			'concept': CE.get_concept_text(concept_dict['concept']),
			'concept_span': concept_dict['concept'],
			'concept_core': core_concept,
			'dependency': CE.get_token_dependency(core_concept), 
			'is_passive': self.is_passive(predicate_dict['predicate_span']),
			'is_at_core': len(concept_dict['concept'])==1 and core_concept == concept_dict['concept'][0],
		}
		role_dict['concept_lemma'] = CE.lemmatize_span(concept_dict['concept'])
		role_dict.update(predicate_dict)
		return role_dict

	def get_pattern_list(self, text):
		parsed_text = self.nlp(text)
		concept_list = CE.get_concept_list(parsed_text, self.min_concept_size)
		#print(list(concept_list))
		#concept_list = (concept for concept in concept_list if len(concept)==1)
		pattern_list = [
			self.get_pattern_from_concept(concept_dict)
			for concept_dict in concept_list
		]
		pattern_list = list(filter(lambda x: x is not None, pattern_list))
		return pattern_list
