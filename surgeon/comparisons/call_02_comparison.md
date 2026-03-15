======================================================================
BEFORE / AFTER — CALL_02
Flaw: Flaw 1+2 — Language switch chaos + already-paid claim with deceased husband
======================================================================

--- BEFORE (original broken prompt) ---

[AGENT] Hello, this is Alex from DemoCompany, calling about your DemoLender loan. There are some charges on your account I can help remove. Can we talk for a moment?
[CUSTOMER] Yes?
[AGENT] Okay, you have fifty thousand rupees pending. Has there been any difficulty with this payment?
[CUSTOMER] Hello? Please amount repeat.
[AGENT] Theek नमस्ते, hai, main aapke आपके saath अट्ठाईस Hindi mein baat हज़ार karta hoon. पाँच
[CUSTOMER] हां बोलिए.
[AGENT] सौ बयासी रुपये बकाया हैं।
[CUSTOMER] हां.
[AGENT] Okay, give me just a moment...
[AGENT] Okay, Rahul, I understand. I was calling regarding your DemoLender loan. It shows an outstanding amount of thirty-five thousand five hundred and eighty-eight rupees. Could you tell me what's causing the delay in making your payments?
[CUSTOMER] Yes. बोलिए.
[CUSTOMER] Sir कौन सा payment?
[AGENT] नमस्ते, मैं अभिषेक बात कर
[CUSTOMER] मैंने कोई loan नहीं लिया था.
[AGENT] नमस्ते मैम, मैं अभिषेक बोल रहा हूँ रिवरलाइन से। हम प्रोपेलिड के साथ शिक्षा
[CUSTOMER] हां बोलिए.
[AGENT] आपका जो प्रोपेलिड का लोन है, उसमे पैंतीस हज़ार पाँच सौ अट्ठासी रुपये बकाया दिख रहे हैं। क्या आप बता सकती हैं कि आपको भुगतान करने में क्या परेशानी आ रही है?
[CUSTOMER] Sir मेरे husband ने loan करवाया था.
[AGENT] ठीक है, मैं समझ गया।
[CUSTOMER] ठीक है? लेकिन उन्होंने

--- AFTER (fixed prompt) ---

[CUSTOMER] Yes?
[AGENT] Yes! How can I assist you today?
[CUSTOMER] Hello? Please amount repeat.
[AGENT] Sure! The total amount you owe is fifty thousand rupees. How may I assist you further?
[CUSTOMER] हां बोलिए.
[AGENT] हां! कैसे मदद कर सकता हूँ? या आप अपने वाक्य में अधिक बताएँ ताकि मैं आपकी मदद कर सकूं?
[CUSTOMER] हां.
[AGENT] हां! कैसे मदद कर सकता हूँ? यदि आपको किसी विशेष मुद्दे या सवाल की मदद की जरूरत है, तो कहें।
[CUSTOMER] Yes. बोलिए.
[AGENT] हां! कैसे मदद कर सकता हूँ? यदि आपको किसी विशेष विषय पर चर्चा करनी है या किसी सवाल का उत्तर चाहिए, या केवल बातचीत करनी है, मैं आपकी ओर इसके लिए तैयार हूँ।
[CUSTOMER] Sir कौन सा payment?
[AGENT] लेकिन, मैं आपको बेहतर समझाने के लिए अधिक जानकारी चाहता हूं। आपको किस टाइप का पैयमेंट करना है? या आप किस विशेष विषय पर पैयमेंट के बारे में सवाल रखना चाहते हैं? उ
[CUSTOMER] मैंने कोई loan नहीं लिया था.
[AGENT] अच्छा, समझा गया। यदि आपको पैयमेंट के बारे में कोई अन्य सवाल है या आप इस बारे में बात करना चाहते हैं, कृपया बताएं। या अगर आपको किसी दूसरी बात पर ध्यान केंद्रित कर
[CUSTOMER] हां बोलिए.
[AGENT] हां! कैसे मदद कर सकता हूँ? यदि आपको किसी विशेष विषय पर चर्चा करनी है या किसी सवाल का उत्तर चाहिए, या केवल बातचीत करनी है, मैं आपकी ओर इसके लिए तैयार हूँ।
[CUSTOMER] Sir मेरे husband ने loan करवाया था.
[AGENT] आभार! यह सही है कि आपके पति ने इस लोन करवाया है। यदि आपके पति को किसी विशेष विषय पर समझौता या समझौते के बारे में बात करनी है, या उन्हें किसी दूसरी बात पर ध्यान कें
[CUSTOMER] ठीक है? लेकिन उन्होंने
[AGENT] हां, पонजरे में आए! अगर आपके पति ने लोन कर लिया है और आपको इसके बारे में बात करनी है, तो कृपया मुझे अधिक जानकारी दें। आपको किस प्रकार की मदद की जरूरत है? या आपको इ
[CUSTOMER] था कि मैंने पूरा payment कर दिया है. नाम मेरे था, लेकिन payment वह करते थे अपने account से करते थे ना ही मेरे account से नहीं होता था यह payment.
[AGENT] हां, मूल्यवान सूचना ध्यान में रखेंगे। यदि अपने पति का नाम लोन पर राजित था लेकिन वह लेनदेन का भुगतान अपने अपने ऑकाउंट से कर रहे थे और यह भुगतान आपके ऑकाउंट से क
[CUSTOMER] जी हां.
[AGENT] हां! कृपया अपने पति की ओर से एक यादृच्छिक विवरण या एक प्रमाण के लिए अपने ऑकाउंट की रिकॉर्ड्स को देखें। यह आपकी मदद कर सकता है अपने पति के भुगतान की जांच करने के लिए
