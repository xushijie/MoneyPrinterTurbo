from haystack import Pipeline, Document
from haystack.components.builders import PromptBuilder
from haystack import component, default_to_dict
from haystack.utils import Jinja2TimeExtension
from haystack.components.generators import HuggingFaceLocalGenerator

from typing import Dict, Any, Optional, Set, List


from app.services.llm import generate_script_response, generate_terms


SCRIPT_BUILDER = "scriptBuilder"
TERM_BUILDER = "termBuilder"

class ChanaAIPileine:
    def __init__(self):
        
        builder = ChanaPromptBuilder()
        llm = ChanaLLMModel()
        
        self.pipeline = Pipeline()
        self.pipeline.add_component(name="builder", instance=builder)
        self.pipeline.add_component(name="llm", instance=llm)

        self.pipeline.connect("builder", "llm")
        
    def run(self, template: str, data: Dict[str, Any], include_outputs_from: Optional[Set[str]] = None):
        
        return self.pipeline.run(data={"builder": {"template": template, "template_variables": data }, "llm": {"template": template}})
    
@component
class ChanaPromptBuilder: 
    
    ## Templates: scriptBuilder, termBuilder
    def __init__( self  ):
        templates = TemplateCenter() 
        self.builders = {
            SCRIPT_BUILDER: PromptBuilder(template=templates.get_template(SCRIPT_BUILDER)),
            TERM_BUILDER: PromptBuilder(template=templates.get_template(TERM_BUILDER))
        }
    
    @component.output_types(prompt=str)
    def run(self, template: Optional[str] = None, template_variables: Optional[Dict[str, Any]] = None, **kwargs):
        if template in self.builders:
            prompt =  self.builders[template].run(template_variables=template_variables, **kwargs)
            return prompt
        return None

@component
class ChanaLLMModel:
    def __init__(self): 
        print("")
    
    @component.output_types(res=str)
    def run(self, template: str, prompt: str): 
        if template == SCRIPT_BUILDER:
            return generate_script_response(prompt)
        elif template == TERM_BUILDER:
            return generate_terms(video_subject=data["video_subject"], video_script=data.get("video_script", ""), amount=data.get("amount", 5))
        else:
            return None
        
    
class TemplateCenter: 
    def __init__(self):
        self.template_map = {SCRIPT_BUILDER: 
            f"""
# Role: Video Script Generator

## Goals:
Generate a script for a video, depending on the subject of the video.

## Constraints:
1. The script is to be returned as a string with the specified number of paragraphs.
2. Do not under any circumstance reference this prompt in your response.
3. Get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. You must not include any type of markdown or formatting in the script, never use a title.
5. Only return the raw content of the script.
6. Do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line.
7. You must not mention the prompt, or anything about the script itself. Also, never talk about the amount of paragraphs or lines. Just write the script.
8. Respond in the same language as the video subject.

# Initialization:
- video subject: {{video_subject}}
- number of paragraphs: {{paragraph_number}}
- language: {{language}}
""".strip(),


TERM_BUILDER:
    f"""
# Role: Video Search Terms Generator

## Goals:
Generate {{amount}} search terms for stock videos, depending on the subject of a video.

## Constrains:
1. the search terms are to be returned as a json-array of strings.
2. each search term should consist of 1-3 words, always add the main subject of the video.
3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
4. the search terms must be related to the subject of the video.
5. reply with english search terms only.

## Output Example:
["search term 1", "search term 2", "search term 3","search term 4","search term 5"]

## Context:
### Video Subject
{{video_subject}}

### Video Script
{{video_script}}

Please note that you must use English for generating video search terms; Chinese is not accepted.
""".strip()}
        
    def get_template(self, key="script_generator"): 
        return self.template_map[key]
    
def test():
    documents = [
        Document(content="Joe lives in Berlin", meta={"name": "doc1"}),
        Document(content="Joe is a software engineer", meta={"name": "doc1"}),
    ]
    new_template = """
        You are a helpful assistant.
        Given these documents, answer the question.
        Documents:
        {% for doc in documents %}
            Document {{ loop.index }}:
            Document name: {{ doc.meta['name'] }}
            {{ doc.content }}
        {% endfor %}

        Question: {{ query }}
        Answer:
        """
    instance = PromptBuilder(template=new_template)
    question = "Where does Joe live?"
    res = instance.run(question)
    print(res)
    
if __name__ == "__main__":
    pipeline = ChanaAIPileine()
    res = pipeline.run(SCRIPT_BUILDER,  
        {"template":SCRIPT_BUILDER, "video_subject": "大海的形成", "paragraph_number": 1, "language": "CN"})
    print(f"res {res}")
    # test()
           
