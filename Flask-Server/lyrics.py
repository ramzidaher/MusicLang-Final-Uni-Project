import fasttext
import pycountry

# Load the pre-trained model
model_path = 'lid.176.bin'

model = fasttext.load_model(model_path)

def get_language_name(iso_code):
    """Fetches the full language name given its ISO code."""
    language = pycountry.languages.get(alpha_2=iso_code)
    if language is not None:
        return language.name
    language = pycountry.languages.get(alpha_3=iso_code)
    if language is not None:
        return language.name
    return iso_code

def predict_languages_for_line(line, threshold=0.01):
    """Predicts languages for a single line, considering the distribution.

    Args:
        line (str): The input text line.
        threshold (float): The minimum percentage to consider for inclusion.
1
    """
    predictions = model.predict(line, k=-1)
    languages, probabilities = predictions
    total_prob = sum(probabilities)

    results = {}
    for lang, prob in zip(languages, probabilities):
        percentage = (prob / total_prob) * 100
        if percentage >= threshold: 
            lang_code = lang.replace('__label__', '')
            lang_name = get_language_name(lang_code)
            results[lang_name] = percentage
    return results

def aggregate_results_from_text(text, initial_threshold=0.01, final_threshold=5.0):
    """Aggregates language detection results across the entire text, applying an initial threshold for detection
    and a final threshold for inclusion in the final results. Re-normalizes percentages of languages meeting the
    final threshold to ensure they sum to 100%.

    Args:
        text (str): The input text.
        initial_threshold (float): Initial threshold for including a language in the intermediate results.
        final_threshold (float): Final threshold for including a language in the final results.

    Returns:
        dict: Aggregated and re-normalized language percentages.
    """
    aggregated_results = {}
    lines = text.split('\n')
    for line in lines:
        if line.strip():  # Ensure the line is not empty
            line_results = predict_languages_for_line(line, initial_threshold)
            for lang, percentage in line_results.items():
                if lang in aggregated_results:
                    aggregated_results[lang] += percentage
                else:
                    aggregated_results[lang] = percentage

    # Normalize to ensure percentages sum to 100%
    total_percentage = sum(aggregated_results.values())
    normalized_results = {lang: (percentage / total_percentage) * 100 for lang, percentage in aggregated_results.items()}

    # Apply the final threshold to filter the results
    final_results = {lang: percentage for lang, percentage in normalized_results.items() if percentage >= final_threshold}

    # Re-normalize final results to ensure they sum up to 100%
    final_total_percentage = sum(final_results.values())
    re_normalized_final_results = {lang: (percentage / final_total_percentage) * 100 for lang, percentage in final_results.items()}

    return re_normalized_final_results

# Your text
text = """
Because you naughty, naughty hey! Mr. Simple
Because you naughty, naughty
다다다다다다다다 다다다다다다다다
다다다다다다다다 다다다다다다다다
슈주 간다!
세상이 내 맘대로 안 된다고 화만 내면 안 돼
그럴 필요 없지 oh oh oh
걱정도 팔자다 작은 일에 너무 연연하지 말자
몸에 좋지 않아
성적이 좋았다가 나빴다가 그런 거지 뭐 흥!
실적이 올랐다가 떨어졌다 그런 때도 있지
어쩌면 괜찮아 쉬어 가는 것도 좋아
모든 것이 때, 때, 때, 때, 때가 있는 거니까
그대가 남자라면 친굴 만나
술 한 잔에 털어버리고 (alright!) alright (alright!)
그대가 여자라면 친굴 만나
수다 떨어 날려버리고 (alright!) alright, alright
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call!)
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call!)
가자 가자 어서 가자 막혔을 땐 돌아가자
골치 아파 죽겠다면 오늘 하루만 놀고 보자
안 그래도 거친 세상
죽어라 뛰면 나만 지쳐
기다려봐 아껴둬 봐
너의 날이 곧 올 테니까
Blow your mind 가라 Mr. Simple
Blow your mind 때가 왔잖아 두려워 말고
Blow your mind 가자 Mr. Simple
Blow your mind 때가 왔잖아 준비 됐잖아
속 썩는 일이 한 두 가지 아닌 세상에 우린 살아
그건 애도 알아 oh oh
뭐 이렇게 어렵나 우리 잘 먹고 잘 자고 또 잘하면
그렇게 하면 되지
그대가 화가 나면 친굴 만나
뒷담화로 풀어버리고 (alright!) alright (alright!)
그대가 괴롭다면 노래 불러
소리 질러 날려버리고 (alright!) alright, alright
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call!)
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call! J call! J call! J call!)
Dance 자유란 게 뭐 그리 별거 있나
Just get it get it
소소한 일탈의 재미
둥둥둥 쿵쿵쿵
살아있는 그댈 느끼고 싶나
Just grab it grab it
가슴 뛰는 내 꿈들의 얘기
둥둥둥 쿵쿵쿵
(Because you naughty, naughty)
이제 걱정 하지마 앞엔 좋은 날이 올 거야
심각한 얘긴 다 뒤로 미뤄두고
오늘은 밝게 웃어봐
그대의 환한 웃음에 모두 기분 좋아져
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call!)
봐라 Mr. Simple, Simple
그대는 그대는 그대로 멋져
봐라 Miss Simple, Simple
그대는 그대로 예뻐 (SJ call!)
가자 가자 어서 가자 막혔을 땐 돌아가자
골치 아파 죽겠다면
오늘 하루만 놀고 보자
안 그래도 거친 세상
죽어라 뛰면 나만 지쳐
기다려봐 아껴둬 봐
너의 날이 곧 올 테니까
Blow your mind 가라 Mr. Simple
Blow your mind 때가 왔잖아 두려워 말고
Blow your mind 가자 Mr. Simple
Blow your mind 가라 Mr. Simple




"""

final_threshold = 5.0  # Example: Only include languages that make up at least 5% of the text
results = aggregate_results_from_text(text, final_threshold=final_threshold)

# Sorting and displaying the refined results
sorted_results = sorted(results.items(), key=lambda item: item[1], reverse=True)
print("Main Languages Detected:")
for lang, percentage in sorted_results:
    print(f"{lang}: {percentage:.2f}%")
