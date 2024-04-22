import google.generativeai as genai
import json

def handler(event, context):

    # Set the model to Gemini 1.5 Pro.
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

    prompt = event.get('prompt', None)
    content_parts = event.get('content_parts', None)
    # TODO - Need to properly escape each string
    #content_parts_as_json = json.dumps(content_parts)


    # Make the LLM request.
    request = [prompt] + content_parts
    response = model.generate_content(request,
                                    request_options={"timeout": 600})
    print(response.text)


    return response.text


