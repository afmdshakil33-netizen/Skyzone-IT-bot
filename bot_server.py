import json
import requests
from flask import Flask, request, jsonify

# =================================================================
# ১. কনফিগারেশন ভ্যারিয়েবল (আপনার দেওয়া টোকেন ও কী এখানে সেট করা হয়েছে)
# =================================================================

# আপনার টেলিগ্রাম বটের টোকেন
TELEGRAM_TOKEN = "8333558740:AAHoXqa8V0E-NAbYxbYU4y15yrBTQzr4QHc" 
# আপনার জেমিনি এপিআই কী
GEMINI_API_KEY = "AIzaSyA6ODnCDBajwqN0dMBzHh4B6NtI7LzF9So" 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

app = Flask(__name__)

# টেলিগ্রাম কমান্ডের জন্য প্রম্পট ডেটা
COMPANY_PROMPTS = {
    "tech": {
        "name": "Buddhi Chorcha (Tech Solutions)",
        "prompt": "Generate 10 unique, positive, human-style user reviews. The reviews must follow these rules: Use 4 Bangla, 3 English, and 3 Banglish reviews — but mix them in random order so the languages don’t follow any fixed sequence. Each review should be written fully in one language. Keep the lengths mixed: some about 20 words, some around 30 words, some 30–40 words. Mention withdrawals or payments through Bkash or Nagad in a natural way. Include real emotions like excitement, relief, doubt, surprise, or satisfaction. Use different styles: feelings, short story, doubtful-but-happy, process-based, analytical, etc. Do not mention the app name in every review; keep it natural and realistic. Avoid robotic tone, repeated patterns, or difficult vocabulary. A few reviews may end with: “thanking Buddhi Chorcha.” Make all 10 reviews fully unique and human-like."
    },
    "fastfood": {
        "name": "ফাস্ট ফুড চেইন",
        "prompt": "একটি ফাস্ট ফুড চেইনের জন্য ১২টি বাংলা রিভিউ তৈরি করুন যেখানে খাবারের স্বাদ দারুণ কিন্তু ডেলিভারি টাইম খুব বেশি এবং প্যাকেজিং দুর্বল। রিভিউগুলো সাধারণ কথোপকথনের মতো হবে।"
    },
    "education": {
        "name": "অনলাইন শিক্ষা প্ল্যাটফর্ম",
        "prompt": "একটি অনলাইন শিক্ষাদান প্ল্যাটফর্মের জন্য ১২টি বাংলা রিভিউ তৈরি করুন যেখানে শিক্ষকেরা অত্যন্ত অভিজ্ঞ কিন্তু কোর্স ফি অনেক বেশি এবং অ্যাপ্লিকেশনটি মাঝেমধ্যে ক্র্যাশ করে। রিভিউগুলোতে গঠনমূলক সমালোচনা থাকবে।"
    }
}

# =================================================================
# ২. টেলিগ্রাম ওয়েবহুক হ্যান্ডলার
# =================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """টেলিগ্রাম থেকে নতুন মেসেজ গ্রহণ করে।"""
    update = request.get_json()
    
    # নিশ্চিত করুন যে মেসেজটি বৈধ এবং চ্যাট আইডি রয়েছে
    if not update or 'message' not in update:
        return jsonify({'status': 'ok'}), 200

    chat_id = update['message']['chat']['id']
    text = update['message'].get('text', '').lower()

    if text.startswith('/'):
        # মেসেজটি কমান্ড কিনা তা পরীক্ষা করা
        command = text.split()[0].replace('/', '')
        
        if command in COMPANY_PROMPTS:
            company_data = COMPANY_PROMPTS[command]
            
            # লোডিং মেসেজ পাঠানো
            send_telegram_message(chat_id, "⏳ রিভিউ তৈরি হচ্ছে... একটু অপেক্ষা করুন।", parse_mode=None)
            
            # জেমিনি এপিআই কল করা
            reviews = generate_reviews_from_gemini(company_data["prompt"])
            
            if reviews:
                # সাফল্যের মেসেজ এবং রিভিউ পাঠানো
                response_text = f"✅ *রিভিউ জেনারেট হলো: {company_data['name']}*\n\n"
                response_text += "\n\n".join([f"**{i+1}.** {r}" for i, r in enumerate(reviews)])
            else:
                response_text = "❌ দুঃখিত, রিভিউ তৈরি করতে ব্যর্থ হয়েছে। Gemini API-এর সাথে সংযোগ বা JSON পার্সিং-এ সমস্যা হতে পারে।"
            
            send_telegram_message(chat_id, response_text, parse_mode='Markdown')
        elif command == 'start':
             # /start কমান্ডের উত্তর
            help_message = (
                "স্বাগতম! আমি Gemini AI দ্বারা চালিত ডাইনামিক রিভিউ জেনারেটর বট।\n\n"
                "রিভিউ জেনারেট করার জন্য যেকোনো একটি কমান্ড ব্যবহার করুন:\n"
                "• `/tech`: Buddhi Chorcha (মিক্সড ভাষা) রিভিউ\n"
                "• `/fastfood`: ফাস্ট ফুড চেইন রিভিউ\n"
                "• `/education`: অনলাইন শিক্ষা রিভিউ\n\n"
                "দ্রষ্টব্য: Gemini-এর রেসপন্স আসতে কিছুটা সময় লাগতে পারে।"
            )
            send_telegram_message(chat_id, help_message, parse_mode=None)
        else:
            send_telegram_message(chat_id, "অজানা কমান্ড। অনুগ্রহ করে `/start` লিখে কমান্ডের তালিকা দেখুন।", parse_mode=None)

    return jsonify({'status': 'ok'}), 200

# =================================================================
# ৩. API এবং টেলিগ্রাম মেসেজ ফাংশন
# =================================================================

def generate_reviews_from_gemini(prompt):
    """Gemini API কে কল করে এবং স্ট্রাকচার্ড JSON থেকে রিভিউগুলি বের করে।"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "reviews": {
                        "type": "ARRAY",
                        "description": "An array of unique customer reviews in Bengali based on the given prompt.",
                        "items": { "type": "STRING" }
                    }
                },
                "required": ["reviews"]
            }
        }
    }
    
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        # JSON পার্সিং
        result = response.json()
        json_text = result['candidates'][0]['content']['parts'][0]['text']
        parsed_json = json.loads(json_text)
        
        # টোকেনগুলি যদি সরাসরি কোডের মধ্যে থাকে, তবে তাদের এনভায়রনমেন্ট ভ্যারিয়েবল দিয়ে প্রতিস্থাপন করার পরামর্শ দেওয়া হয়
        return parsed_json.get("reviews", [])
    except Exception as e:
        # এরর হলে কনসোলে প্রিন্ট করা
        print(f"Gemini API কল ব্যর্থ: {e}")
        return []

def send_telegram_message(chat_id, text, parse_mode='Markdown'):
    """টেলিগ্রাম Bot API-এর মাধ্যমে মেসেজটি ফেরত পাঠায়।"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"টেলিগ্রাম মেসেজ পাঠাতে ব্যর্থ: {e}")


if __name__ == '__main__':
    # এই সার্ভারটি চালানোর জন্য এটি একটি পাবলিক URL-এ হোস্ট করা আবশ্যক 
    print("সার্ভার শুরু হচ্ছে...")
    app.run(host='0.0.0.0', port=5000)
