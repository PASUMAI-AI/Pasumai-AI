let token=localStorage.getItem('gram_token')||'';
let me=null,activeRole=localStorage.getItem('gram_login_role')||'farmer',currentLang=localStorage.getItem('gram_lang')||'en',currentState='Tamil Nadu',currentPage='';
let charts={},mapObj=null,networkMarkers=[];
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>'₹'+Number(n||0).toLocaleString('en-IN',{maximumFractionDigits:0}), num=n=>Number(n||0).toLocaleString('en-IN',{maximumFractionDigits:1});

const LANGS=window.LANGS={en:['English','en-IN'],hi:['हिन्दी','hi-IN'],mr:['मराठी','mr-IN'],ta:['தமிழ்','ta-IN'],te:['తెలుగు','te-IN'],bn:['বাংলা','bn-IN'],gu:['ગુજરાતી','gu-IN'],kn:['ಕನ್ನಡ','kn-IN'],ml:['മലയാളം','ml-IN'],pa:['ਪੰਜਾਬੀ','pa-IN'],or:['ଓଡ଼ିଆ','or-IN'],as:['অসমীয়া','as-IN'],ur:['اردو','ur-IN'],ne:['नेपाली','ne-IN'],sa:['संस्कृतम्','sa-IN'],ks:['कॉशुर','ks-IN'],sd:['سنڌي','sd-IN'],kok:['कोंकणी','kok-IN'],mai:['मैथिली','mai-IN'],doi:['डोगरी','doi-IN'],brx:['बड़ो','brx-IN'],mni:['মৈতৈলোন্','mni-IN'],sat:['ᱥᱟᱱᱛᱟᱲᱤ','sat-IN'],raj:['राजस्थानी','hi-IN']};
const EN={dashboard:'Dashboard',crops:'Crops & Forecasts',market:'Market & Offers',preorders:'Pre-Orders',transport:'Transport & Groups',paymentsRewards:'Payments & Rewards',profile:'Profile',feedback:'Feedback',grievances:'Grievances',linkIndia:'Link India',chats:'Chats',discover:'Discover Harvest',orders:'My Orders',bulk:'Bulk & Shared Logistics',rewards:'Rewards',connectBuyers:'Connect Buyers',usersKyc:'Users & KYC',markets:'Markets',payments:'Payments',stateAnalytics:'State Analytics',feedbackReq:'Feedback & Requirements',securityActions:'Security Actions',todayIncome:"Today's Income",totalIncome:'Total Income',openOffers:'Open Buyer Offers',openHarvests:'Open Harvests',todayRecommendation:"Today's Recommendation",gramVerified:'GRAM AI Verified',notVerified:'KYC Required',addCrop:'Add Verified Crop',upcoming:'My Harvests',openForBuyers:'Open for Buyers',closed:'Closed',priceForecast:'1 / 3 / 7 Day Forecast',generate:'Generate GRAM AI Recommendation',finalRecommendation:'Final GRAM AI Recommendation',bestMarket:'Best Market',expectedNet:'Expected Net Income',reliability:'Forecast Reliability',marketPredictions:'Predictions for Markets Near You',currentPrice:'Current Price',predicted1:'1 Day',predicted3:'3 Days',predicted7:'7 Days',buyerOffers:'Buyer Offers',verifiedBuyers:'Top Verified Buyers',viewDetails:'View Details',accept:'Accept',decline:'Decline',wait:'Wait',negotiate:'Negotiate',chat:'Chat',token:'Token Money',securePayment:'Secure Payment',qualityGrade:'AI Quality Grade',livePhoto:'Live Produce Photo',gps:'Use Live GPS',certificate:'Quality Certificate',transportCost:'Transport Cost',distance:'Distance',location:'Location',groupSelling:'Group Selling',myTransport:'My Transport',sharedTransport:'Shared Transport',rewardPoints:'GramPoints',redeem:'Redeem',validTill:'Valid till',cancellation:'Cancellation Health',profileDetails:'Profile Details',bankDetails:'Bank & Payout Details',kyc:'KYC + Live Photo Verification',verifiedBadge:'Verified Badge',submit:'Submit',rating:'Rating',orderFeedback:'Mandatory Order Feedback',complaint:'Complaint',raiseGrievance:'Raise Grievance',networkMap:'India Network Map',sellers:'Sellers',buyers:'Buyers',combineSell:'Start Combined Selling',message:'Message',area:'Area',purchased:'Crops Purchased',tracking:'Order Tracking',spend:'Total Purchase Value',availableHarvests:'Verified Harvests in Tamil Nadu',placeOrder:'Place Order',placePreorder:'Place Pre-Order',bulkBuying:'Buyer Pool',nearbyBuyers:'Nearby Buyers',nearbyTransport:'Route-share Transport',revenue:'Platform Revenue',complaints:'Complaints',pendingKyc:'Pending KYC',risk:'Risk / Security',block:'Block',unblock:'Unblock',terminate:'Terminate',warn:'Warn',solution:'Resolution',status:'Status',details:'Details',state:'State',district:'District',crop:'Crop',quantity:'Quantity',price:'Price',date:'Date',farmer:'Farmer',buyer:'Buyer',admin:'Admin',logout:'Logout',language:'Language',home:'Home',search:'Search',notification:'Notifications',why:'Why?',paymentStatus:'Payment Status',refund:'Refund',cashback:'Cashback',warning:'Warning',penalty:'Penalty',noData:'No data yet',allIndia:'All India'};
const PACK={
 hi:{dashboard:'डैशबोर्ड',crops:'फसल और पूर्वानुमान',market:'बाज़ार और ऑफ़र',preorders:'प्री-ऑर्डर',transport:'परिवहन और समूह',paymentsRewards:'भुगतान और पुरस्कार',profile:'प्रोफ़ाइल',feedback:'फीडबैक',grievances:'शिकायतें',linkIndia:'लिंक इंडिया',chats:'चैट',discover:'फसल खोजें',orders:'मेरे ऑर्डर',bulk:'समूह खरीद और साझा परिवहन',rewards:'पुरस्कार',connectBuyers:'खरीदारों से जुड़ें',usersKyc:'उपयोगकर्ता और KYC',markets:'बाज़ार',payments:'भुगतान',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'फीडबैक और आवश्यकताएँ',securityActions:'सुरक्षा कार्रवाई',todayIncome:'आज की आय',todayRecommendation:'आज की सलाह',addCrop:'सत्यापित फसल जोड़ें',upcoming:'मेरी फसलें',priceForecast:'1 / 3 / 7 दिन पूर्वानुमान',generate:'GRAM AI सलाह बनाएं',finalRecommendation:'अंतिम GRAM AI सलाह',bestMarket:'सर्वश्रेष्ठ बाज़ार',expectedNet:'अपेक्षित शुद्ध आय',buyerOffers:'खरीदार ऑफ़र',verifiedBuyers:'शीर्ष सत्यापित खरीदार',accept:'स्वीकार',decline:'अस्वीकार',wait:'प्रतीक्षा',negotiate:'बातचीत',chat:'चैट',securePayment:'सुरक्षित भुगतान',qualityGrade:'AI गुणवत्ता ग्रेड',livePhoto:'लाइव फसल फोटो',gps:'लाइव GPS',certificate:'गुणवत्ता प्रमाणपत्र',rewardPoints:'ग्रामपॉइंट्स',redeem:'रिडीम',kyc:'KYC + लाइव फोटो सत्यापन',networkMap:'भारत नेटवर्क मानचित्र',logout:'लॉगआउट'},
 mr:{dashboard:'डॅशबोर्ड',crops:'पिके आणि अंदाज',market:'बाजार आणि ऑफर्स',preorders:'प्री-ऑर्डर',transport:'वाहतूक आणि गट',paymentsRewards:'पेमेंट आणि रिवॉर्ड्स',profile:'प्रोफाइल',feedback:'अभिप्राय',grievances:'तक्रारी',linkIndia:'लिंक इंडिया',chats:'चॅट्स',discover:'पीक शोधा',orders:'माझे ऑर्डर्स',bulk:'सामूहिक खरेदी आणि शेअर्ड लॉजिस्टिक्स',rewards:'रिवॉर्ड्स',connectBuyers:'खरेदीदारांशी जोडा',usersKyc:'वापरकर्ते आणि KYC',markets:'बाजार',payments:'पेमेंट्स',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'अभिप्राय आणि गरजा',securityActions:'सुरक्षा कारवाई',todayIncome:'आजचे उत्पन्न',todayRecommendation:'आजची शिफारस',addCrop:'सत्यापित पीक जोडा',upcoming:'माझी कापणी',openForBuyers:'खरेदीदारांसाठी खुले',priceForecast:'1 / 3 / 7 दिवसांचा अंदाज',generate:'GRAM AI शिफारस तयार करा',finalRecommendation:'अंतिम GRAM AI शिफारस',bestMarket:'सर्वोत्तम बाजार',expectedNet:'अपेक्षित निव्वळ उत्पन्न',marketPredictions:'जवळच्या बाजारांचे अंदाज',buyerOffers:'खरेदीदार ऑफर्स',verifiedBuyers:'शीर्ष सत्यापित खरेदीदार',viewDetails:'तपशील पहा',accept:'स्वीकारा',decline:'नकार',wait:'थांबा',negotiate:'वाटाघाटी',chat:'चॅट',token:'टोकन रक्कम',securePayment:'सुरक्षित पेमेंट',qualityGrade:'AI गुणवत्ता ग्रेड',livePhoto:'लाइव्ह पीक फोटो',gps:'लाइव्ह GPS वापरा',certificate:'गुणवत्ता प्रमाणपत्र',transportCost:'वाहतूक खर्च',distance:'अंतर',groupSelling:'गट विक्री',myTransport:'माझी वाहतूक',sharedTransport:'शेअर्ड वाहतूक',rewardPoints:'ग्रामपॉइंट्स',redeem:'रिडीम',validTill:'वैधता',cancellation:'रद्द करण्याची स्थिती',profileDetails:'प्रोफाइल तपशील',bankDetails:'बँक आणि पेआउट तपशील',kyc:'KYC + लाइव्ह फोटो पडताळणी',verifiedBadge:'सत्यापित बॅज',orderFeedback:'अनिवार्य ऑर्डर अभिप्राय',raiseGrievance:'तक्रार नोंदवा',networkMap:'भारत नेटवर्क नकाशा',combineSell:'एकत्र विक्री सुरू करा',logout:'लॉगआउट'},
 ta:{dashboard:'முகப்பு',crops:'பயிர்கள் & விலை கணிப்பு',market:'சந்தை & சலுகைகள்',preorders:'முன்பதிவுகள்',transport:'போக்குவரத்து & குழுக்கள்',paymentsRewards:'பணம் & வெகுமதிகள்',profile:'சுயவிவரம்',feedback:'கருத்து',grievances:'புகார்கள்',linkIndia:'இந்தியா இணைப்பு',chats:'அரட்டைகள்',discover:'அறுவடை தேடல்',orders:'என் ஆர்டர்கள்',bulk:'கூட்டு வாங்குதல் & பகிர்வு போக்குவரத்து',rewards:'வெகுமதிகள்',connectBuyers:'வாங்குபவர்களை இணைக்கவும்',usersKyc:'பயனர்கள் & KYC',markets:'சந்தைகள்',payments:'பணம்',stateAnalytics:'மாநில பகுப்பாய்வு',todayIncome:'இன்றைய வருமானம்',todayRecommendation:'இன்றைய பரிந்துரை',addCrop:'சரிபார்க்கப்பட்ட பயிர் சேர்க்க',priceForecast:'1 / 3 / 7 நாள் கணிப்பு',generate:'GRAM AI பரிந்துரை உருவாக்கு',finalRecommendation:'இறுதி GRAM AI பரிந்துரை',bestMarket:'சிறந்த சந்தை',buyerOffers:'வாங்குபவர் சலுகைகள்',verifiedBuyers:'சரிபார்க்கப்பட்ட முன்னணி வாங்குபவர்கள்',accept:'ஏற்க',decline:'நிராகரி',wait:'காத்திரு',negotiate:'பேச்சுவார்த்தை',chat:'அரட்டை',securePayment:'பாதுகாப்பான கட்டணம்',qualityGrade:'AI தரம்',livePhoto:'நேரடி பயிர் படம்',gps:'நேரடி GPS',rewardPoints:'GramPoints',redeem:'மீட்டெடு',kyc:'KYC + நேரடி படம் சரிபார்ப்பு',networkMap:'இந்தியா வலை வரைபடம்',logout:'வெளியேறு'},
 te:{dashboard:'డ్యాష్‌బోర్డ్',crops:'పంటలు & అంచనాలు',market:'మార్కెట్ & ఆఫర్లు',preorders:'ప్రీ-ఆర్డర్లు',transport:'రవాణా & గ్రూపులు',paymentsRewards:'చెల్లింపులు & రివార్డులు',profile:'ప్రొఫైల్',feedback:'అభిప్రాయం',grievances:'ఫిర్యాదులు',linkIndia:'లింక్ ఇండియా',chats:'చాట్లు',discover:'హార్వెస్ట్ కనుగొనండి',orders:'నా ఆర్డర్లు',bulk:'సమూహ కొనుగోలు & షేర్ లాజిస్టిక్స్',rewards:'రివార్డులు',connectBuyers:'కొనుగోలుదారులను కలపండి',usersKyc:'వినియోగదారులు & KYC',markets:'మార్కెట్లు',payments:'చెల్లింపులు',stateAnalytics:'రాష్ట్ర విశ్లేషణ',todayIncome:'ఈరోజు ఆదాయం',todayRecommendation:'ఈరోజు సిఫార్సు',addCrop:'ధృవీకరించిన పంట జోడించండి',priceForecast:'1 / 3 / 7 రోజుల అంచనా',generate:'GRAM AI సిఫార్సు',finalRecommendation:'చివరి GRAM AI సిఫార్సు',bestMarket:'ఉత్తమ మార్కెట్',buyerOffers:'కొనుగోలుదారు ఆఫర్లు',verifiedBuyers:'అగ్ర ధృవీకరించిన కొనుగోలుదారులు',accept:'అంగీకరించు',decline:'తిరస్కరించు',wait:'వేచి ఉండు',negotiate:'చర్చ',chat:'చాట్',securePayment:'సురక్షిత చెల్లింపు',qualityGrade:'AI నాణ్యత గ్రేడ్',livePhoto:'లైవ్ పంట ఫోటో',gps:'లైవ్ GPS',rewardPoints:'GramPoints',redeem:'రిడీమ్',kyc:'KYC + లైవ్ ఫోటో ధృవీకరణ',networkMap:'భారత నెట్‌వర్క్ మ్యాప్',logout:'లాగ్ అవుట్'},
 bn:{dashboard:'ড্যাশবোর্ড',crops:'ফসল ও পূর্বাভাস',market:'বাজার ও অফার',preorders:'প্রি-অর্ডার',transport:'পরিবহন ও গ্রুপ',paymentsRewards:'পেমেন্ট ও পুরস্কার',profile:'প্রোফাইল',feedback:'মতামত',grievances:'অভিযোগ',linkIndia:'লিংক ইন্ডিয়া',chats:'চ্যাট',discover:'ফসল খুঁজুন',orders:'আমার অর্ডার',rewards:'পুরস্কার',todayIncome:'আজকের আয়',todayRecommendation:'আজকের পরামর্শ',logout:'লগআউট'},
 gu:{dashboard:'ડેશબોર્ડ',crops:'પાક અને આગાહી',market:'બજાર અને ઑફર',preorders:'પ્રી-ઓર્ડર',transport:'પરિવહન અને જૂથ',paymentsRewards:'ચુકવણી અને પુરસ્કાર',profile:'પ્રોફાઇલ',feedback:'પ્રતિસાદ',grievances:'ફરિયાદો',linkIndia:'લિંક ઇન્ડિયા',chats:'ચેટ',discover:'પાક શોધો',orders:'મારા ઓર્ડર',rewards:'પુરસ્કાર',todayIncome:'આજની આવક',todayRecommendation:'આજની ભલામણ',logout:'લૉગઆઉટ'},
 kn:{dashboard:'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',crops:'ಬೆಳೆಗಳು & ಮುನ್ಸೂಚನೆ',market:'ಮಾರುಕಟ್ಟೆ & ಆಫರ್',preorders:'ಪ್ರೀ-ಆರ್ಡರ್',transport:'ಸಾರಿಗೆ & ಗುಂಪು',paymentsRewards:'ಪಾವತಿ & ಬಹುಮಾನ',profile:'ಪ್ರೊಫೈಲ್',feedback:'ಪ್ರತಿಕ್ರಿಯೆ',grievances:'ದೂರುಗಳು',linkIndia:'ಲಿಂಕ್ ಇಂಡಿಯಾ',chats:'ಚಾಟ್',discover:'ಬೆಳೆ ಹುಡುಕಿ',orders:'ನನ್ನ ಆರ್ಡರ್‌ಗಳು',rewards:'ಬಹುಮಾನಗಳು',todayIncome:'ಇಂದಿನ ಆದಾಯ',todayRecommendation:'ಇಂದಿನ ಶಿಫಾರಸು',logout:'ಲಾಗ್ ಔಟ್'},
 ml:{dashboard:'ഡാഷ്ബോർഡ്',crops:'വിളകൾ & പ്രവചനം',market:'മാർക്കറ്റ് & ഓഫറുകൾ',preorders:'പ്രീ-ഓർഡർ',transport:'ഗതാഗതം & ഗ്രൂപ്പുകൾ',paymentsRewards:'പേയ്മെന്റ് & റിവാർഡ്',profile:'പ്രൊഫൈൽ',feedback:'ഫീഡ്ബാക്ക്',grievances:'പരാതികൾ',linkIndia:'ലിങ്ക് ഇന്ത്യ',chats:'ചാറ്റുകൾ',discover:'വിള കണ്ടെത്തുക',orders:'എന്റെ ഓർഡറുകൾ',rewards:'റിവാർഡുകൾ',todayIncome:'ഇന്നത്തെ വരുമാനം',todayRecommendation:'ഇന്നത്തെ ശുപാർശ',logout:'ലോഗ് ഔട്ട്'},
 pa:{dashboard:'ਡੈਸ਼ਬੋਰਡ',crops:'ਫਸਲਾਂ ਅਤੇ ਅਨੁਮਾਨ',market:'ਮਾਰਕੀਟ ਅਤੇ ਆਫਰ',preorders:'ਪ੍ਰੀ-ਆਰਡਰ',transport:'ਆਵਾਜਾਈ ਅਤੇ ਗਰੁੱਪ',paymentsRewards:'ਭੁਗਤਾਨ ਅਤੇ ਇਨਾਮ',profile:'ਪ੍ਰੋਫਾਈਲ',feedback:'ਫੀਡਬੈਕ',grievances:'ਸ਼ਿਕਾਇਤਾਂ',linkIndia:'ਲਿੰਕ ਇੰਡੀਆ',chats:'ਚੈਟ',discover:'ਫਸਲ ਲੱਭੋ',orders:'ਮੇਰੇ ਆਰਡਰ',rewards:'ਇਨਾਮ',todayIncome:'ਅੱਜ ਦੀ ਆਮਦਨ',todayRecommendation:'ਅੱਜ ਦੀ ਸਿਫਾਰਸ਼',logout:'ਲਾਗ ਆਉਟ'},
 or:{dashboard:'ଡ୍ୟାସବୋର୍ଡ',crops:'ଫସଲ ଓ ପୂର୍ବାନୁମାନ',market:'ବଜାର ଓ ଅଫର',preorders:'ପ୍ରି-ଅର୍ଡର',transport:'ପରିବହନ ଓ ଗୋଷ୍ଠୀ',paymentsRewards:'ପେମେଣ୍ଟ ଓ ପୁରସ୍କାର',profile:'ପ୍ରୋଫାଇଲ',feedback:'ମତାମତ',grievances:'ଅଭିଯୋଗ',linkIndia:'ଲିଙ୍କ ଇଣ୍ଡିଆ',chats:'ଚାଟ୍',todayIncome:'ଆଜିର ଆୟ',logout:'ଲଗଆଉଟ'},
 as:{dashboard:'ডেশ্বব’ৰ্ড',crops:'শস্য আৰু পূৰ্বানুমান',market:'বজাৰ আৰু অফাৰ',preorders:'প্ৰি-অৰ্ডাৰ',transport:'পৰিবহন আৰু গোট',paymentsRewards:'পেমেণ্ট আৰু পুৰস্কাৰ',profile:'প্ৰফাইল',feedback:'মতামত',grievances:'অভিযোগ',linkIndia:'লিংক ইণ্ডিয়া',chats:'চেট',todayIncome:'আজিৰ আয়',logout:'লগআউট'},
 ur:{dashboard:'ڈیش بورڈ',crops:'فصلیں اور پیش گوئی',market:'بازار اور آفر',preorders:'پری آرڈر',transport:'ٹرانسپورٹ اور گروپس',paymentsRewards:'ادائیگی اور انعامات',profile:'پروفائل',feedback:'رائے',grievances:'شکایات',linkIndia:'لنک انڈیا',chats:'چیٹ',todayIncome:'آج کی آمدنی',logout:'لاگ آؤٹ'},
 ne:{dashboard:'ड्यासबोर्ड',crops:'बाली र पूर्वानुमान',market:'बजार र अफर',preorders:'प्रि-अर्डर',transport:'यातायात र समूह',paymentsRewards:'भुक्तानी र पुरस्कार',profile:'प्रोफाइल',feedback:'प्रतिक्रिया',grievances:'गुनासो',linkIndia:'लिंक इन्डिया',chats:'च्याट',todayIncome:'आजको आम्दानी',logout:'लगआउट'},
 sa:{dashboard:'मुखपटलम्',crops:'सस्यानि तथा पूर्वानुमानः',market:'विपणिः तथा प्रस्तावाः',preorders:'पूर्वादेशाः',transport:'परिवहनं तथा समूहाः',paymentsRewards:'भुगतानं तथा पुरस्काराः',profile:'परिचयः',feedback:'प्रतिपुष्टिः',grievances:'शिकायताः',linkIndia:'भारतसम्पर्कः',chats:'संवादाः',todayIncome:'अद्यतन आयः',logout:'निर्गमनम्'},
 ks:{dashboard:'ڈیش بورڈ',crops:'فصل تہٕ پیش گوئی',market:'بازار تہٕ آفر',preorders:'پری آرڈر',transport:'ٹرانسپورٹ تہٕ گروپ',paymentsRewards:'ادائیگی تہٕ انعام',profile:'پروفائل',feedback:'رائے',grievances:'شکایت',linkIndia:'لنک انڈیا',chats:'چیٹ',todayIncome:'اَزُک آمدن',logout:'لاگ آؤٹ'},
 sd:{dashboard:'ڊيش بورڊ',crops:'فصل ۽ اڳڪٿي',market:'مارڪيٽ ۽ آفر',preorders:'پري آرڊر',transport:'ٽرانسپورٽ ۽ گروپ',paymentsRewards:'ادائگي ۽ انعام',profile:'پروفائل',feedback:'راءِ',grievances:'شڪايتون',linkIndia:'لنڪ انڊيا',chats:'چيٽ',todayIncome:'اڄ جي آمدني',logout:'لاگ آئوٽ'},
 kok:{dashboard:'डॅशबोर्ड',crops:'पिकां आनी अंदाज',market:'बाजार आनी ऑफर',preorders:'प्री-ऑर्डर',transport:'वाहतूक आनी गट',paymentsRewards:'पेमेंट आनी रिवॉर्ड',profile:'प्रोफाइल',feedback:'अभिप्राय',grievances:'तक्रारी',linkIndia:'लिंक इंडिया',chats:'चॅट',todayIncome:'आजचें उत्पन्न',logout:'लॉगआऊट'},
 mai:{dashboard:'डैशबोर्ड',crops:'फसल आ पूर्वानुमान',market:'बजार आ ऑफर',preorders:'प्री-ऑर्डर',transport:'परिवहन आ समूह',paymentsRewards:'भुगतान आ पुरस्कार',profile:'प्रोफाइल',feedback:'प्रतिक्रिया',grievances:'शिकायत',linkIndia:'लिंक इंडिया',chats:'चैट',todayIncome:'आइ केर आय',logout:'लॉगआउट'},
 doi:{dashboard:'डैशबोर्ड',crops:'फसल ते अनुमान',market:'बजार ते ऑफर',preorders:'प्री-ऑर्डर',transport:'ट्रांसपोर्ट ते ग्रुप',paymentsRewards:'भुगतान ते इनाम',profile:'प्रोफाइल',feedback:'फीडबैक',grievances:'शिकायतां',linkIndia:'लिंक इंडिया',chats:'चैट',todayIncome:'अज्ज दी आमदनी',logout:'लॉगआउट'},
 brx:{dashboard:'डेशबर्ड',crops:'आबाद आरो अनुमान',market:'बाजार आरो अफार',preorders:'प्रि-अर्डार',transport:'ट्रान्सपर्ट आरो हानजा',paymentsRewards:'पेमेंट आरो इनाम',profile:'प्रफाइल',feedback:'फिडबेक',grievances:'आजद',linkIndia:'लिंक इन्डिया',chats:'चेट',todayIncome:'दिनैनि आय',logout:'लगआउट'},
 mni:{dashboard:'দাশবোর্দ',crops:'লৌউ & অচুম্বা',market:'কৈথেল & অফর',preorders:'প্রী-অর্ডর',transport:'পুথোক-পুশিন & গ্রুপ',paymentsRewards:'শেল & রিওয়ার্দ',profile:'প্রোফাইল',feedback:'ফীদবেক',grievances:'অভিযোগ',linkIndia:'লিংক ইন্ডিয়া',chats:'চ্যাট',todayIncome:'ঙসিগী চনবী',logout:'লগ আউট'},
 sat:{dashboard:'ᱰᱮᱥᱵᱚᱨᱰ',crops:'ᱪᱟᱥ & ᱟᱱᱫᱟᱡ',market:'ᱦᱟᱴ & ᱚᱯᱷᱟᱨ',preorders:'ᱯᱨᱤ-ᱚᱨᱰᱟᱨ',transport:'ᱜᱟᱹᱰᱤ & ᱫᱚᱞ',paymentsRewards:'ᱯᱮᱢᱮᱱᱴ & ᱨᱤᱣᱟᱨᱰ',profile:'ᱯᱨᱚᱯᱷᱟᱭᱤᱞ',feedback:'ᱯᱷᱤᱰᱵᱮᱠ',grievances:'ᱟᱨᱡᱤ',linkIndia:'ᱞᱤᱝᱠ ᱤᱱᱰᱤᱭᱟ',chats:'ᱪᱮᱴ',todayIncome:'ᱛᱮᱦᱮᱧ ᱟᱭ',logout:'ᱞᱚᱜᱟᱣᱩᱴ'},
 raj:{dashboard:'डैशबोर्ड',crops:'फसल अर अंदाज',market:'मंडी अर ऑफर',preorders:'प्री-ऑर्डर',transport:'ढुलाई अर समूह',paymentsRewards:'भुगतान अर इनाम',profile:'प्रोफाइल',feedback:'राय',grievances:'शिकायत',linkIndia:'लिंक इंडिया',chats:'चैट',todayIncome:'आज री कमाई',logout:'लॉगआउट'}
};

Object.assign(EN,{heroTitle:'Better selling decisions, not just market prices.',heroText:'Forecast prices, verify quality, compare net income, connect with trusted buyers and protect transactions.',secureAccess:'Secure role-based access',loginAs:'Login as whom?',farmerHint:'Sell smarter',buyerHint:'Source reliably',adminHint:'Maintain platform',selectedRole:'Selected role',login:'Login',register:'Register',emailPassword:'Email + Password',mobileOtp:'Mobile + OTP',email:'Email',password:'Password',mobile:'Mobile Number',sendOtp:'Send OTP',otp:'6-digit OTP',verifyLogin:'Verify & Login',kycNote:'KYC/Aadhaar-ready verification is available after login. Full Aadhaar numbers are never stored.',name:'Full Name',chatHint:'Ask in your language',chatWelcome:'Namaste! Ask me about prices, buyers, pre-orders, payments, transport, rewards or grievances.'});
Object.assign(PACK.mr,{loginAs:'कोण म्हणून लॉगिन करायचे?',login:'लॉगिन',register:'नोंदणी',email:'ईमेल',password:'पासवर्ड',mobile:'मोबाईल क्रमांक',secureAccess:'सुरक्षित भूमिका-आधारित प्रवेश',chatHint:'तुमच्या भाषेत विचारा'});
Object.assign(PACK.hi,{loginAs:'किस रूप में लॉगिन करें?',login:'लॉगिन',register:'पंजीकरण',email:'ईमेल',password:'पासवर्ड',mobile:'मोबाइल नंबर',secureAccess:'सुरक्षित भूमिका-आधारित प्रवेश',chatHint:'अपनी भाषा में पूछें'});
Object.assign(PACK.ta,{loginAs:'யாராக உள்நுழைய வேண்டும்?',login:'உள்நுழை',register:'பதிவு',email:'மின்னஞ்சல்',password:'கடவுச்சொல்',mobile:'மொபைல் எண்',secureAccess:'பாதுகாப்பான பங்கு அடிப்படையிலான அணுகல்',chatHint:'உங்கள் மொழியில் கேளுங்கள்'});
Object.assign(PACK.te,{loginAs:'ఎవరిగా లాగిన్ అవ్వాలి?',login:'లాగిన్',register:'నమోదు',email:'ఇమెయిల్',password:'పాస్‌వర్డ్',mobile:'మొబైల్ నంబర్',secureAccess:'సురక్షిత పాత్ర ఆధారిత యాక్సెస్',chatHint:'మీ భాషలో అడగండి'});
const NAVX={
 bn:{bulk:'সম্মিলিত ক্রয় ও লজিস্টিকস',connectBuyers:'ক্রেতাদের সাথে যুক্ত হন',usersKyc:'ব্যবহারকারী ও KYC',markets:'বাজার',payments:'পেমেন্ট',stateAnalytics:'রাজ্য বিশ্লেষণ',feedbackReq:'মতামত ও প্রয়োজন',securityActions:'নিরাপত্তা ব্যবস্থা'},
 gu:{bulk:'સમૂહ ખરીદી અને લોજિસ્ટિક્સ',connectBuyers:'ખરીદદારો સાથે જોડાઓ',usersKyc:'વપરાશકર્તા અને KYC',markets:'બજારો',payments:'ચુકવણી',stateAnalytics:'રાજ્ય વિશ્લેષણ',feedbackReq:'પ્રતિસાદ અને જરૂરિયાતો',securityActions:'સુરક્ષા કાર્યવાહી'},
 kn:{bulk:'ಸಮೂಹ ಖರೀದಿ & ಲಾಜಿಸ್ಟಿಕ್ಸ್',connectBuyers:'ಖರೀದಿದಾರರನ್ನು ಸಂಪರ್ಕಿಸಿ',usersKyc:'ಬಳಕೆದಾರರು & KYC',markets:'ಮಾರುಕಟ್ಟೆಗಳು',payments:'ಪಾವತಿಗಳು',stateAnalytics:'ರಾಜ್ಯ ವಿಶ್ಲೇಷಣೆ',feedbackReq:'ಪ್ರತಿಕ್ರಿಯೆ & ಅಗತ್ಯಗಳು',securityActions:'ಭದ್ರತಾ ಕ್ರಮಗಳು'},
 ml:{bulk:'കൂട്ടവാങ്ങൽ & ലോജിസ്റ്റിക്സ്',connectBuyers:'വാങ്ങുന്നവരുമായി ബന്ധപ്പെടുക',usersKyc:'ഉപയോക്താക്കൾ & KYC',markets:'മാർക്കറ്റുകൾ',payments:'പേയ്മെന്റുകൾ',stateAnalytics:'സംസ്ഥാന വിശകലനം',feedbackReq:'ഫീഡ്ബാക്ക് & ആവശ്യങ്ങൾ',securityActions:'സുരക്ഷാ നടപടികൾ'},
 pa:{bulk:'ਸਮੂਹ ਖਰੀਦ ਅਤੇ ਲਾਜਿਸਟਿਕਸ',connectBuyers:'ਖਰੀਦਦਾਰਾਂ ਨਾਲ ਜੁੜੋ',usersKyc:'ਉਪਭੋਗਤਾ ਅਤੇ KYC',markets:'ਮਾਰਕੀਟਾਂ',payments:'ਭੁਗਤਾਨ',stateAnalytics:'ਰਾਜ ਵਿਸ਼ਲੇਸ਼ਣ',feedbackReq:'ਫੀਡਬੈਕ ਅਤੇ ਲੋੜਾਂ',securityActions:'ਸੁਰੱਖਿਆ ਕਾਰਵਾਈ'},
 or:{bulk:'ସମୁହ କ୍ରୟ ଓ ଲଜିଷ୍ଟିକ୍ସ',connectBuyers:'କ୍ରେତାଙ୍କ ସହ ଯୋଡନ୍ତୁ',usersKyc:'ବ୍ୟବହାରକାରୀ ଓ KYC',markets:'ବଜାର',payments:'ପେମେଣ୍ଟ',stateAnalytics:'ରାଜ୍ୟ ବିଶ୍ଳେଷଣ',feedbackReq:'ମତାମତ ଓ ଆବଶ୍ୟକତା',securityActions:'ସୁରକ୍ଷା କାର୍ଯ୍ୟ'},
 as:{bulk:'সমূহ ক্ৰয় আৰু লজিষ্টিক্স',connectBuyers:'ক্ৰেতাৰ সৈতে সংযোগ',usersKyc:'ব্যৱহাৰকাৰী আৰু KYC',markets:'বজাৰ',payments:'পেমেণ্ট',stateAnalytics:'ৰাজ্য বিশ্লেষণ',feedbackReq:'মতামত আৰু প্ৰয়োজন',securityActions:'সুৰক্ষা ব্যৱস্থা'},
 ur:{bulk:'مشترکہ خرید اور لاجسٹکس',connectBuyers:'خریداروں سے جڑیں',usersKyc:'صارفین اور KYC',markets:'بازار',payments:'ادائیگیاں',stateAnalytics:'ریاستی تجزیہ',feedbackReq:'رائے اور ضروریات',securityActions:'سکیورٹی ایکشن'},
 ne:{bulk:'समूह खरिद र लजिस्टिक्स',connectBuyers:'खरिदकर्तासँग जोडिनुहोस्',usersKyc:'प्रयोगकर्ता र KYC',markets:'बजारहरू',payments:'भुक्तानी',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'प्रतिक्रिया र आवश्यकता',securityActions:'सुरक्षा कार्य'},
 sa:{bulk:'समूहक्रयः तथा परिवहनम्',connectBuyers:'क्रेतृभिः सम्पर्कः',usersKyc:'उपयोक्तारः तथा KYC',markets:'विपण्यः',payments:'भुगतानानि',stateAnalytics:'राज्यविश्लेषणम्',feedbackReq:'प्रतिपुष्टिः तथा आवश्यकताः',securityActions:'सुरक्षाकार्याणि'},
 ks:{bulk:'مشترکہ خرید تہٕ لاجسٹکس',connectBuyers:'خریدارن سۭتۍ رابطہ',usersKyc:'صارف تہٕ KYC',markets:'بازار',payments:'ادائیگی',stateAnalytics:'ریاست تجزیہ',feedbackReq:'رائے تہٕ ضرورت',securityActions:'سکیورٹی کارروائی'},
 sd:{bulk:'گڏيل خريد ۽ لاجسٽڪس',connectBuyers:'خريدارن سان ڳنڍيو',usersKyc:'استعمال ڪندڙ ۽ KYC',markets:'مارڪيٽون',payments:'ادائگيون',stateAnalytics:'رياستي تجزيو',feedbackReq:'راءِ ۽ ضرورتون',securityActions:'سيڪيورٽي ڪارروائي'},
 kok:{bulk:'सामूहिक खरेदी आनी लॉजिस्टिक्स',connectBuyers:'खरेदीदारांक जोडात',usersKyc:'वापरपी आनी KYC',markets:'बाजार',payments:'पेमेंट्स',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'अभिप्राय आनी गरजा',securityActions:'सुरक्षा कारवाई'},
 mai:{bulk:'समूह खरीद आ लजिस्टिक्स',connectBuyers:'खरीदारसँ जुड़ू',usersKyc:'उपयोगकर्ता आ KYC',markets:'बजार',payments:'भुगतान',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'प्रतिक्रिया आ आवश्यकता',securityActions:'सुरक्षा कार्रवाई'},
 doi:{bulk:'सांझी खरीद ते लॉजिस्टिक्स',connectBuyers:'खरीदारें कन्नै जुड़ो',usersKyc:'यूजर ते KYC',markets:'बजार',payments:'भुगतान',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'फीडबैक ते जरूरतां',securityActions:'सुरक्षा कारवाई'},
 brx:{bulk:'जथाय खरिद आरो लजिस्टिक्स',connectBuyers:'बायग्रा लोगोसे सोमोन्दो',usersKyc:'बाहायग्रा आरो KYC',markets:'बाजार',payments:'पेमेंट',stateAnalytics:'राज्य बिजिरनाय',feedbackReq:'फिडबेक आरो गोनांथि',securityActions:'रैखाथि हाबा'},
 mni:{bulk:'পুন্না লৈবা & লজিস্টিকস',connectBuyers:'লৈরকপশিংগা শম্ননবা',usersKyc:'শিজিন্নরিবা & KYC',markets:'কৈথেলশিং',payments:'শেল পীবা',stateAnalytics:'রাজ্য বিশ্লেষণ',feedbackReq:'ফীদবেক & দরকার',securityActions:'সিকিউরিটি থবক'},
 sat:{bulk:'ᱡᱚᱛᱚ ᱠᱤᱨᱤᱧ & ᱞᱚᱡᱤᱥᱴᱤᱠᱥ',connectBuyers:'ᱠᱤᱨᱤᱧᱤᱡ ᱥᱟᱶ ᱡᱚᱲᱟᱣ',usersKyc:'ᱭᱩᱡᱟᱨ & KYC',markets:'ᱦᱟᱴ',payments:'ᱯᱮᱢᱮᱱᱴ',stateAnalytics:'ᱨᱟᱡᱽ ᱵᱤᱥᱞᱮᱥᱚᱱ',feedbackReq:'ᱯᱷᱤᱰᱵᱮᱠ & ᱫᱟᱨᱠᱟᱨ',securityActions:'ᱥᱮᱠᱭᱩᱨᱤᱴᱤ'},
 raj:{bulk:'सांझी खरीद अर लॉजिस्टिक्स',connectBuyers:'खरीदारां सूं जुड़ो',usersKyc:'यूजर अर KYC',markets:'मंडियां',payments:'भुगतान',stateAnalytics:'राज्य विश्लेषण',feedbackReq:'राय अर जरूरत',securityActions:'सुरक्षा कार्रवाई'}
};
Object.entries(NAVX).forEach(([k,v])=>PACK[k]=Object.assign(PACK[k]||{},v));
function tr(k){return (PACK[currentLang]&&PACK[currentLang][k])||EN[k]||k}

async function api(path,opts={}){opts.headers={...(opts.headers||{})};if(!(opts.body instanceof FormData))opts.headers['Content-Type']='application/json';if(token)opts.headers.Authorization=`Bearer ${token}`;let r=await fetch(path,opts),text=await r.text(),d={};try{d=text?JSON.parse(text):{}}catch{d={detail:text||`Request failed (${r.status})`}}if(r.status===401){logout();throw Error('Session expired')}if(!r.ok)throw Error(d.detail||`Request failed (${r.status})`);return d}
function toast(msg){let t=$('toast');t.textContent=msg;t.classList.remove('hidden');setTimeout(()=>t.classList.add('hidden'),3500)}
function fillLangs(){['authLang','langSelect'].forEach(id=>{let el=$(id);if(!el)return;el.innerHTML=Object.entries(LANGS).map(([k,v])=>`<option value="${k}">${v[0]}</option>`).join('');el.value=currentLang})}
function setLanguage(v){currentLang=v;window.currentLang=v;localStorage.setItem('gram_lang',v);fillLangs();document.documentElement.lang=v;document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=tr(e.dataset.i18n));if(me){renderNav();route(currentPage||'dashboard')}if(window.I18N)window.I18N.setLang(v).then(()=>{if(window.GramSaathi)window.GramSaathi.onLanguageChange()});else if(window.GramSaathi)window.GramSaathi.onLanguageChange()}
function localizedWelcome(){let x={mr:'नमस्कार! मी GRAM Saathi. पीक भाव, बाजार, खरेदीदार, पेमेंट, वाहतूक, रिवॉर्ड किंवा तक्रारीबद्दल विचारा.',hi:'नमस्ते! मैं GRAM Saathi हूँ। फसल भाव, बाज़ार, खरीदार, भुगतान, परिवहन, पुरस्कार या शिकायत पूछें।',ta:'வணக்கம்! நான் GRAM Saathi. பயிர் விலை, சந்தை, வாங்குபவர், பணம், போக்குவரத்து, வெகுமதி அல்லது புகார் பற்றி கேளுங்கள்.',te:'నమస్కారం! నేను GRAM Saathi. పంట ధర, మార్కెట్, కొనుగోలుదారు, చెల్లింపు, రవాణా, రివార్డు లేదా ఫిర్యాదు గురించి అడగండి.'};return x[currentLang]||'Namaste! I am GRAM Saathi. Ask about crop prices, markets, buyers, payments, transport, rewards or grievances.'}
function selectRole(r){activeRole=r;localStorage.setItem('gram_login_role',r);document.querySelectorAll('[data-role]').forEach(b=>b.classList.toggle('selected',b.dataset.role===r));if($('selectedRoleLabel'))$('selectedRoleLabel').textContent=tr(r);let demo={farmer:['farmer@gram.ai','Farmer@123'],buyer:['buyer@gram.ai','Buyer@123'],admin:['admin@gram.ai','Admin@123']}[r];if($('email'))$('email').value=demo[0];if($('password'))$('password').value=demo[1]}
function showAuthMode(m){$('loginBox').classList.toggle('hidden',m!=='login');$('registerBox').classList.toggle('hidden',m!=='register');$('loginTab').classList.toggle('active',m==='login');$('registerTab').classList.toggle('active',m==='register')}
function showLoginMethod(m){$('emailBox').classList.toggle('hidden',m!=='email');$('otpBox').classList.toggle('hidden',m!=='otp')}
async function login(){try{let d=await api('/auth/login',{method:'POST',body:JSON.stringify({email:$('email').value,password:$('password').value})});token=d.access_token;localStorage.setItem('gram_token',token);me=await api('/auth/me');if(me.role!==activeRole){logout();throw Error(`This account is ${me.role}, not ${activeRole}`)}boot()}catch(e){$('authMessage').textContent=e.message}}
async function sendOtp(){try{let d=await api('/auth/otp/request',{method:'POST',body:JSON.stringify({phone:$('loginPhone').value})});$('otpEntry').classList.remove('hidden');$('otpMessage').textContent=d.demo_otp?`Demo OTP: ${d.demo_otp}`:'OTP sent'}catch(e){$('otpMessage').textContent=e.message}}
async function verifyOtp(){try{let d=await api('/auth/otp/verify',{method:'POST',body:JSON.stringify({phone:$('loginPhone').value,otp:$('loginOtp').value})});token=d.access_token;localStorage.setItem('gram_token',token);me=await api('/auth/me');boot()}catch(e){toast(e.message)}}
async function registerUser(){try{let d=await api('/auth/register',{method:'POST',body:JSON.stringify({name:$('rName').value,email:$('rEmail').value,phone:$('rPhone').value,district:$('rDistrict').value,state:'Tamil Nadu',role:activeRole})});$('regMessage').textContent=d.message||'Registered'}catch(e){$('regMessage').textContent=e.message}}
function logout(){token='';me=null;localStorage.removeItem('gram_token');$('appShell').classList.add('hidden');$('auth').classList.remove('hidden');$('gsFab').classList.add('hidden')}
async function boot(){if(!me)me=await api('/auth/me');$('auth').classList.add('hidden');$('appShell').classList.remove('hidden');$('gsFab').classList.remove('hidden');$('userName').textContent=me.name;$('userRole').textContent=tr(me.role);$('userInitial').textContent=me.name[0];$('portalName').textContent=`${tr(me.role)} Portal`;if(me.role==='farmer')$('stateSelect').closest('label').style.display='none';else{$('stateSelect').closest('label').style.display='flex';fillStates()}renderNav();route('dashboard')}
async function fillStates(){let states=['Tamil Nadu','Maharashtra','Karnataka','Gujarat','Punjab','Rajasthan','Madhya Pradesh','Uttar Pradesh','West Bengal','Telangana','Kerala','Odisha','Bihar','Assam','Delhi'];$('stateSelect').innerHTML=states.map(s=>`<option>${s}</option>`).join('');$('stateSelect').value=currentState}
function changeState(v){currentState=v;route(currentPage)}

const NAV={farmer:[['dashboard','🏠'],['crops','🌾'],['market','🧺'],['preorders','🤝'],['transport','🚚'],['paymentsRewards','💳'],['profile','👤'],['feedback','⭐'],['grievances','🛡'],['linkIndia','🗺'],['chats','💬']],buyer:[['dashboard','🏠'],['discover','🌾'],['preorders','📅'],['orders','📦'],['bulk','👥'],['rewards','🎁'],['profile','👤'],['feedback','⭐'],['grievances','🛡'],['connectBuyers','🗺'],['chats','💬']],admin:[['dashboard','📊'],['usersKyc','🪪'],['markets','🌐'],['payments','💳'],['grievances','🛡'],['stateAnalytics','📈'],['feedbackReq','💬'],['securityActions','🔐']]};
function renderNav(){$('nav').innerHTML=NAV[me.role].map(([k,ic])=>`<button class="nav-btn ${currentPage===k?'active':''}" onclick="route('${k}')"><span>${ic}</span><b>${tr(k)}</b></button>`).join('')}
function setTitle(k){currentPage=k;$('pageTitle').textContent=tr(k);$('breadcrumb').textContent=`GRAM AI • ${me.role==='farmer'?'Tamil Nadu':currentState}`;renderNav()}
async function route(k){setTitle(k);currentPage=k;destroyCharts();if(mapObj){mapObj.remove();mapObj=null}try{if(me.role==='farmer')return await farmerRoute(k);if(me.role==='buyer')return await buyerRoute(k);return await adminRoute(k)}catch(e){$('content').innerHTML=`<div class="card error">${esc(e.message)}</div>`}finally{if(window.I18N)setTimeout(()=>window.I18N.apply(document.body),0)}}
function destroyCharts(){Object.values(charts).forEach(c=>{try{c.destroy()}catch{}});charts={}}
function card(label,value,sub='',cls=''){return `<div class="stat-card ${cls}"><small>${label}</small><b>${value}</b>${sub?`<span>${sub}</span>`:''}</div>`}
function badge(ok){return ok?`<span class="verified-badge">✓ ${tr('gramVerified')}</span>`:`<span class="danger-tag">${tr('notVerified')}</span>`}
function section(title,body,actions=''){return `<section class="card"><div class="section-head"><h2>${title}</h2>${actions}</div>${body}</section>`}
function button(text,fn,cls='secondary'){return `<button class="${cls}" onclick="${fn}">${text}</button>`}

async function farmerRoute(k){

  if(k==='dashboard')return farmerDashboard();

  if(k==='crops')return farmerCrops();

  if(k==='market')return farmerMarket();

  if(k==='preorders')return farmerPreorders();

  if(k==='transport')return farmerTransport();

  if(k==='paymentsRewards')return paymentsRewardsPage();

  if(k==='profile')return profilePage();

  if(k==='feedback')return farmerFeedbackPage();

  if(k==='grievances')return farmerGrievancePage();

  if(k==='linkIndia')return networkPage('farmer');

  if(k==='chats')return chatsPage();

}
/* WhatsApp inventory: crops the farmer declared over WhatsApp, verified by YOLO. */
function waStatusTag(it){
 let v=it.verification_status||'awaiting_image';
 if(v==='verified')return '<span class="tag">✓ Image verified</span>';
 if(v==='mismatch')return '<span class="tag danger">⚠ Crop mismatch</span>';
 return '<span class="tag warn">📸 Awaiting photo</span>';
}
function waCertTag(it){
 let cs=it.certificate_status||'pending';
 if(cs==='issued')return `<span class="tag">📄 ${esc(it.certificate_number||'Issued')}</span>`;
 if(cs==='failed')return '<span class="tag danger">Certificate failed</span>';
 return '<span class="tag warn">Certificate pending</span>';
}
async function whatsappInventorySection(){
 let d;
 try{ d=await api('/api/whatsapp/inventory'); }catch(e){ return ''; }
 if(!d.items||!d.items.length)return section('🌾 My Crop Inventory',
   `<div class="empty">Tell GRAM Saathi <b>"I have 30 kg rice"</b> in the chat, then attach a photo with the 📷 button to verify quality.</div>`);
 let rows=d.items.map(it=>{
  let conf=it.confidence!=null?` (${(it.confidence*100).toFixed(1)}%)`:'';
  let yolo=it.grade?`Quality grade ${esc(it.grade)}${conf}`:'Not inspected yet';
  let det=it.detected_crop&&it.detected_crop!==it.crop?`<small>Image suggests: ${esc(it.detected_crop)}</small>`:'';
  return `<div class="list-item"><div>
    <b>🌾 ${esc(it.crop)} — ${Number(it.quantity).toLocaleString('en-IN')} ${esc(it.unit||'kg')}</b>
    <small>${esc(yolo)}</small>${det}
    <small>${esc(it.created_at||'')}</small>
   </div><div class="actions">${waStatusTag(it)}${waCertTag(it)}</div></div>`;
 }).join('');
 return section('🌾 My Crop Inventory',`<div class="simple-list">${rows}</div>`);
}

async function farmerDashboard(){let d=await api('/api/v2/v3/dashboard');let notes=await api('/api/notifications');$('content').innerHTML=`<div class="hero-reco"><div><small>${tr('todayRecommendation')}</small><h2>${esc(d.recommendation)}</h2><p>GRAM AI combines local price movement, demand and logistics before you commit a sale.</p></div><div>${badge(d.kyc.status==='VERIFIED'&&d.kyc.live_check)}</div></div><div class="grid stats-4">${card(tr('todayIncome'),fmt(d.today_income),'Revenue credited today','green')}${card(tr('totalIncome'),fmt(d.total_income),'Lifetime recorded sales')}${card(tr('openOffers'),d.open_offers,'Waiting for your action')}${card(tr('rewardPoints'),d.reward_points,'Redeem for transport / fee benefits')}</div>${section(tr('notification'),notes.slice(0,6).map(n=>`<div class="list-item"><div><b>${esc(n.title)}</b><small>${esc(n.message)}</small></div><span class="tag">${esc(n.severity)}</span></div>`).join('')||`<div class="empty">${tr('noData')}</div>`)} ${await whatsappInventorySection()}`}

async function farmerCrops(){let hs=await api('/api/v2/v3/harvests');let crops=await api('/api/crops');let markets=await api('/api/markets?state=Tamil Nadu');$('content').innerHTML=`<div class="toolbar"><button class="primary" onclick="openVerifiedCropFlow()">＋ ${tr('addCrop')}</button><span class="soft-note">📍 Tamil Nadu is fixed for your selling portal. Use Link India to explore other states.</span></div>${section(tr('upcoming'),hs.length?`<div class="harvest-grid">${hs.map(h=>`<div class="harvest-card"><div class="harvest-top"><div><span class="crop-icon">🌾</span><b>${esc(h.crop)} • ${esc(h.variety)}</b></div><span class="tag ${h.buyer_visible?'success':''}">${h.buyer_visible?tr('openForBuyers'):tr('closed')}</span></div><div class="mini-grid"><span>${tr('quantity')}<b>${num(h.available_quantity_qtl)} qtl</b></span><span>${tr('date')}<b>${esc(h.expected_harvest_date)}</b></span><span>${tr('qualityGrade')}<b>${esc(h.grade_expected||'Pending')}</b></span><span>${tr('token')}<b>${fmt(h.token_amount)}</b></span></div>${h.certificate_url?button('📄 '+tr('certificate'),`openCertificate('${h.certificate_url}')`):''}</div>`).join('')}</div>`:`<div class="empty">No harvests yet. Add a verified crop using live GPS + live photo.</div>`)}${section(tr('priceForecast'),`<div class="forecast-form"><select id="fcrop" class="control">${crops.map(c=>`<option>${esc(c.name)}</option>`).join('')}</select><select id="fmarket" class="control">${markets.map(m=>`<option value="${m.id}">${esc(m.name)} • ${esc(m.district)}</option>`).join('')}</select><input id="fqty" class="control" type="number" value="10" min="1"><button class="primary" onclick="runFarmerForecast()">✨ ${tr('generate')}</button></div><div id="forecastResult"></div>`)} `}

function getGPS() {
  return new Promise((resolve, reject) =>
    navigator.geolocation
      ? navigator.geolocation.getCurrentPosition(
          p =>
            resolve({
              lat: p.coords.latitude,
              lon: p.coords.longitude
            }),
          e => reject(Error(e.message)),
          {
            enableHighAccuracy: true,
            timeout: 12000
          }
        )
      : reject(Error('GPS not supported'))
  );
}


/* =========================================================
   VERIFIED CROP FLOW
========================================================= */

let cropVerify = null;


function openVerifiedCropFlow() {

  cropVerify = {
    step: 1,
    g: null,
    ver: null,
    crop: 'Tomato'
  };

  renderVerifiedCropStep();

  $('modal').classList.remove('hidden');
}


/* =========================================================
   RENDER VERIFIED CROP WIZARD
========================================================= */

function renderVerifiedCropStep() {

  const step = cropVerify?.step || 1;

  $('modalBody').innerHTML = `

    <div class="verified-crop-modal">

      <div class="modal-title-row">

        <h2>
          🌾 ${tr('addCrop')}
        </h2>

      </div>


      <!-- STEP INDICATOR -->

      <div class="crop-stepper">


        <div
          class="crop-step
          ${step === 1 ? 'active' : step > 1 ? 'done' : ''}"
        >

          <span>
            ${step > 1 ? '✓' : '1'}
          </span>

          <b>
            Verify Location
          </b>

        </div>


        <div
          class="crop-step
          ${step === 2 ? 'active' : step > 2 ? 'done' : ''}"
        >

          <span>
            ${step > 2 ? '✓' : '2'}
          </span>

          <b>
            Live Photo + AI Grade
          </b>

        </div>


        <div
          class="crop-step
          ${step === 3 ? 'active' : ''}"
        >

          <span>
            3
          </span>

          <b>
            Sale & Token
          </b>

        </div>


      </div>


      <div id="verifiedCropStepContent">

        ${verifiedCropStepHtml(step)}

      </div>


    </div>

  `;
}


/* =========================================================
   STEP CONTENT
========================================================= */

function verifiedCropStepHtml(step) {


  /* ==========================
     STEP 1 - GPS
  ========================== */

  if (step === 1) {

    return `

      <div class="crop-step-panel">

        <h3>
          Step 1 — Verify Location
        </h3>

        <p class="step-description">

          A valid location is mandatory before the produce
          photo can be graded or listed.

        </p>


        <div class="field">

          <label>
            ${tr('crop')}
          </label>

          <input
            id="vcrop"
            class="control"
            value="${esc(cropVerify.crop || 'Tomato')}"
            placeholder="Enter crop name"
          >

        </div>


        <div class="gps-action-box">

          <button
            class="primary"
            onclick="captureCropGPS()"
          >

            📍 ${tr('gps')}

          </button>


          <button
            class="secondary"
            onclick="manualCropGPS()"
          >

            Enter Coordinates Manually

          </button>

        </div>


        <div
          id="gpsText"
          class="
            verification-status
            ${
              cropVerify.g
                ? 'success-status'
                : 'pending-status'
            }
          "
        >

          ${
            cropVerify.g
              ? `
                ✓ Location verified —
                ${Number(cropVerify.g.lat).toFixed(5)},
                ${Number(cropVerify.g.lon).toFixed(5)}
              `
              : 'Location not verified.'
          }

        </div>


        ${
          cropVerify.g
            ? `

              <button
                class="primary wide"
                onclick="goToCropStep(2)"
              >

                Continue to Live Photo →

              </button>

            `
            : ''
        }


      </div>

    `;
  }



  /* ==========================
     STEP 2 - YOLO
  ========================== */

  if (step === 2) {

    return `

      <div class="crop-step-panel">

        <h3>
          Step 2 — Upload / Capture Produce Photo
        </h3>


        <p class="step-description">

          Grade cannot be entered manually.
          GRAM AI will automatically analyse the produce
          and assign Grade A, B or C.

        </p>


        <div class="verified-location-summary">

          📍 Verified GPS:

          <b>

            ${Number(cropVerify.g.lat).toFixed(5)},
            ${Number(cropVerify.g.lon).toFixed(5)}

          </b>

        </div>


        <div class="field">

          <label>
            ${tr('livePhoto')}
          </label>

          <input
            id="vphoto"
            class="control"
            type="file"
            accept="image/*"
            capture="environment"
          >


          <small>

            On supported phones, the camera will be requested.
            On desktop, use webcam/file capture.

          </small>

        </div>


        <div class="action-row">

          <button
            class="secondary"
            onclick="goToCropStep(1)"
          >

            ← Back

          </button>


          <button
            class="primary"
            onclick="runYoloVerification()"
          >

            🤖 Run Automatic Grade

          </button>

        </div>


        <div id="verifyResult"></div>


      </div>

    `;
  }



  /* ==========================
     STEP 3 - SALE + TOKEN
  ========================== */

  if (step === 3) {

    const d = cropVerify.ver;

    return `

      <div class="crop-step-panel">

        <h3>
          Step 3 — Sale Details & Secure Token
        </h3>


        <!-- QUALITY RESULT -->

        <div class="quality-result">

          <div>

            <small>
              ${tr('qualityGrade')}
            </small>

            <b class="grade-big">

              Grade ${esc(d.grade)}

            </b>

            <span>

              ${num(d.confidence_percent)}% confidence

            </span>

          </div>


          <div>

            ${
              d.validated_crop_model
                ? `
                  <span class="verified-badge">
                    ✓ GRAM AI YOLO Verified
                  </span>
                `
                : `
                  <span class="warn-tag">
                    Demo grading mode
                  </span>
                `
            }

          </div>

        </div>



        <!-- SALE DETAILS -->

        <div class="form-grid">


          <div class="field">

            <label>
              ${tr('quantity')} (qtl)
            </label>

            <input
              id="vqty"
              class="control"
              type="number"
              value="10"
              min="1"
            >

          </div>



          <div class="field">

            <label>
              Variety
            </label>

            <input
              id="vvar"
              class="control"
              value="Premium"
            >

          </div>



          <div class="field">

            <label>
              ${tr('price')} / qtl
            </label>

            <input
              id="vprice"
              class="control"
              type="number"
              value="2400"
              min="1"
            >

          </div>



          <div class="field">

            <label>
              Harvest Date
            </label>

            <input
              id="vdate"
              class="control"
              type="date"
            >

          </div>



          <!-- TOKEN -->

          <div class="field token-highlight">

            <label>

              🔐 Minimum Token to Accept Order (₹)

            </label>


            <input
              id="vtoken"
              class="control"
              type="number"
              value="500"
              min="1"
              oninput="updateTokenPreview()"
            >


            <small>

              Buyer must pay this secure token before
              the accepted order becomes confirmed.

            </small>

          </div>



          <!-- TRANSPORT RATE -->

          <div class="field">

            <label>
              Transport ₹ / km
            </label>

            <input
              id="vrate"
              class="control"
              type="number"
              value="22"
              min="0"
            >

          </div>



          <div class="field">

            <label>
              Delivery Radius (km)
            </label>

            <input
              id="vradius"
              class="control"
              type="number"
              value="250"
              min="0"
            >

          </div>



          <div class="field">

            <label>
              Packaging
            </label>

            <input
              id="vpack"
              class="control"
              value="Crates"
            >

          </div>


        </div>



        <!-- TOKEN INFORMATION -->

        <div class="token-rule-box">

          <b>
            🔒 Secure Order Rule
          </b>


          <p>

            When you accept a buyer's order,
            its status will remain

            <strong>
              AWAITING TOKEN
            </strong>

            until the required payment is completed.

          </p>


          <p>

            Required Token:

            <strong id="tokenPreview">
              ₹500
            </strong>

          </p>

        </div>



        <!-- OPTIONS -->

        <div class="check-row">


          <label>

            <input
              id="vbuyers"
              type="checkbox"
              checked
            >

            ${tr('openForBuyers')}

          </label>


          <label>

            <input
              id="vtransport"
              type="checkbox"
              checked
            >

            Seller transport available

          </label>


        </div>



        <div class="action-row">


          <button
            class="secondary"
            onclick="goToCropStep(2)"
          >

            ← Back

          </button>


          <button
            class="primary"
            onclick="publishVerifiedCrop()"
          >

            Publish Verified Crop

          </button>


        </div>


      </div>

    `;
  }


  return '';
}



/* =========================================================
   CAPTURE GPS
========================================================= */

function captureCropGPS() {

  if (!navigator.geolocation) {

    toast(
      'GPS is not supported in this browser'
    );

    return;
  }


  navigator.geolocation.getCurrentPosition(

    pos => {


      cropVerify.g = {

        lat: pos.coords.latitude,

        lon: pos.coords.longitude,

        source: 'gps'

      };


      if ($('vcrop')) {

        cropVerify.crop =
          $('vcrop').value.trim() || 'Tomato';

      }


      renderVerifiedCropStep();


      toast(
        'Location verified successfully'
      );

    },


    () => {

      toast(
        'Unable to access GPS. Please allow location permission or enter coordinates manually.'
      );

    },


    {

      enableHighAccuracy: true,

      timeout: 15000

    }

  );
}



/* =========================================================
   MANUAL GPS
========================================================= */

function manualCropGPS() {

  const lat =
    prompt('Enter latitude');


  if (lat === null) return;


  const lon =
    prompt('Enter longitude');


  if (lon === null) return;


  const latitude =
    Number(lat);


  const longitude =
    Number(lon);


  if (

    !Number.isFinite(latitude) ||

    !Number.isFinite(longitude) ||

    latitude < -90 ||

    latitude > 90 ||

    longitude < -180 ||

    longitude > 180

  ) {

    toast(
      'Please enter valid coordinates'
    );

    return;

  }


  cropVerify.g = {

    lat: latitude,

    lon: longitude,

    source: 'manual'

  };


  if ($('vcrop')) {

    cropVerify.crop =
      $('vcrop').value.trim() || 'Tomato';

  }


  renderVerifiedCropStep();


  toast(
    'Location verified manually'
  );

}



/* =========================================================
   CHANGE STEP
========================================================= */

function goToCropStep(step) {


  if (

    step === 2 &&

    !cropVerify.g

  ) {

    toast(
      'Please verify GPS first'
    );

    return;

  }


  if (

    step === 3 &&

    !cropVerify.ver

  ) {

    toast(
      'Please complete AI quality grading first'
    );

    return;

  }


  if ($('vcrop')) {

    cropVerify.crop =
      $('vcrop').value.trim() || 'Tomato';

  }


  cropVerify.step =
    step;


  renderVerifiedCropStep();

}



/* =========================================================
   TOKEN PREVIEW
========================================================= */

function updateTokenPreview() {

  const value =
    Number(
      $('vtoken')?.value || 0
    );


  if ($('tokenPreview')) {

    $('tokenPreview').textContent =
      `₹${value.toLocaleString('en-IN')}`;

  }

}



/* =========================================================
   YOLO QUALITY VERIFICATION
========================================================= */

async function runYoloVerification() {

  try {


    if (!cropVerify?.g) {

      throw new Error(
        'Verify GPS first'
      );

    }


    const photoInput =
      $('vphoto');


    if (

      !photoInput ||

      !photoInput.files ||

      !photoInput.files[0]

    ) {

      throw new Error(
        'Capture a live produce photo first'
      );

    }


    const cropName =
      cropVerify.crop || 'Tomato';


    const fd =
      new FormData();


    fd.append(
      'crop',
      cropName
    );


    fd.append(
      'latitude',
      String(cropVerify.g.lat)
    );


    fd.append(
      'longitude',
      String(cropVerify.g.lon)
    );


    fd.append(
      'location_source',
      cropVerify.g.source || 'gps'
    );


    fd.append(
      'photo',
      photoInput.files[0]
    );


    if ($('verifyResult')) {

      $('verifyResult').innerHTML = `

        <div class="ai-processing">

          🤖 GRAM AI is analysing the produce image...

        </div>

      `;

    }


    const d =
      await api(

        '/api/produce/inspect',

        {

          method: 'POST',

          body: fd

        }

      );


    cropVerify.ver =
      d;


    cropVerify.step =
      3;


    renderVerifiedCropStep();


    toast(

      `Quality verified: Grade ${d.grade}`

    );


  }

  catch (e) {

    toast(e.message);

  }

}



/* =========================================================
   PUBLISH VERIFIED CROP
========================================================= */

async function publishVerifiedCrop() {

  try {


    if (

      !cropVerify ||

      !cropVerify.ver

    ) {

      throw new Error(
        'Complete GRAM AI quality verification first'
      );

    }


    const date =
      $('vdate').value;


    if (!date) {

      throw new Error(
        'Select harvest date'
      );

    }


    const quantity =
      Number(
        $('vqty').value
      );


    const price =
      Number(
        $('vprice').value
      );


    const tokenAmount =
      Number(
        $('vtoken').value
      );


    const transportRate =
      Number(
        $('vrate').value
      );


    const radius =
      Number(
        $('vradius').value
      );


    if (

      !quantity ||

      quantity <= 0

    ) {

      throw new Error(
        'Enter valid quantity'
      );

    }


    if (

      !price ||

      price <= 0

    ) {

      throw new Error(
        'Enter valid selling price'
      );

    }


    if (

      !tokenAmount ||

      tokenAmount <= 0

    ) {

      throw new Error(
        'Enter a valid minimum token amount'
      );

    }



    /* CREATE LISTING */

    await api(

      '/api/listings',

      {

        method: 'POST',

        body: JSON.stringify({

          verification_id:
            cropVerify.ver.verification_id,

          variety:
            $('vvar').value,

          quantity_qtl:
            quantity,

          ask_price:
            price,

          harvest_date:
            date,

          packaging:
            $('vpack').value,

          min_order_qtl:
            1,

          seller_transport:
            $('vtransport').checked,

          transport_cost_per_km:
            transportRate,

          delivery_radius_km:
            radius,

          loading_included:
            true,

          quality_notes:
            'Live GPS + image verified by GRAM AI'

        })

      }

    );



    /* CREATE VERIFIED HARVEST */

    await api(

      `/api/v2/v3/harvest-from-verification` +

      `?verification_id=${encodeURIComponent(
        cropVerify.ver.verification_id
      )}` +

      `&quantity_qtl=${encodeURIComponent(
        quantity
      )}` +

      `&harvest_date=${encodeURIComponent(
        date
      )}` +

      `&variety=${encodeURIComponent(
        $('vvar').value
      )}` +

      `&ask_price=${encodeURIComponent(
        price
      )}` +

      `&token_amount=${encodeURIComponent(
        tokenAmount
      )}` +

      `&buyer_visible=${encodeURIComponent(
        $('vbuyers').checked
      )}` +

      `&transport_rate_per_km=${encodeURIComponent(
        transportRate
      )}` +

      `&transport_radius_km=${encodeURIComponent(
        radius
      )}`,

      {

        method: 'POST'

      }

    );


    toast(
      'Verified crop published for buyers'
    );


    closeModal();


    farmerCrops();


  }

  catch (e) {

    toast(e.message);

  }

}



/* =========================================================
   QUALITY CERTIFICATE
========================================================= */

async function openCertificate(url) {

  try {


    const r =
      await fetch(

        url,

        {

          headers: {

            Authorization:
              `Bearer ${token}`

          }

        }

      );


    if (!r.ok) {

      throw new Error(
        'Certificate unavailable'
      );

    }


    const blob =
      await r.blob();


    const objectUrl =
      URL.createObjectURL(blob);


    window.open(
      objectUrl,
      '_blank'
    );


    setTimeout(

      () =>
        URL.revokeObjectURL(
          objectUrl
        ),

      60000

    );


  }

  catch (e) {

    toast(e.message);

  }

}



/* =========================================================
   GRAM AI REVIEW FOR EACH MARKET
========================================================= */

function marketReviewBadge(
  market,
  bestMarket
) {

  let action =
    String(
      market.action || ''
    ).toUpperCase();


  /*
     If backend already generated an action,
     use that action first.
  */

  if (
    action.includes('SELL')
  ) {

    action =
      'SELL';

  }

  else if (
    action.includes('WAIT')
  ) {

    action =
      'WAIT';

  }

  else if (
    action.includes('SHIFT')
  ) {

    action =
      'SHIFT';

  }

  else {


    const currentPrice =
      Number(
        market.current_price || 0
      );


    const futurePrice =
      Number(
        market.predicted_price || 0
      );


    const currentNet =
      Number(
        market.net_realizable || 0
      );


    const bestNet =
      Number(
        bestMarket?.net_realizable || 0
      );



    /*
       If this market gives substantially
       lower net income than the best market,
       recommend shifting.
    */

    if (

      bestNet > 0 &&

      currentNet > 0 &&

      currentNet <
        bestNet * 0.95

    ) {

      action =
        'SHIFT';

    }


    /*
       If the future price is meaningfully
       higher, recommend waiting.
    */

    else if (

      currentPrice > 0 &&

      futurePrice >
        currentPrice * 1.03

    ) {

      action =
        'WAIT';

    }


    else {

      action =
        'SELL';

    }

  }



  let cls =
    'review-sell';


  let icon =
    '✓';


  if (
    action === 'WAIT'
  ) {

    cls =
      'review-wait';

    icon =
      '⏳';

  }


  if (
    action === 'SHIFT'
  ) {

    cls =
      'review-shift';

    icon =
      '↗';

  }


  return `

    <span class="market-review ${cls}">

      ${icon} ${action}

    </span>

  `;

}



/* =========================================================
   FARMER FORECAST + GRAM AI RECOMMENDATION
========================================================= */

async function runFarmerForecast() {

  const crop =
    $('fcrop').value;


  const marketId =
    Number(
      $('fmarket').value
    );


  const quantity =
    Number(
      $('fqty').value
    );


  try {


    const [
      forecastData,
      comparisonData
    ] =

      await Promise.all([

        api(

          `/api/ml/forecast` +

          `?crop=${encodeURIComponent(crop)}` +

          `&market_id=${marketId}`

        ),


        api(

          `/api/ml/compare` +

          `?crop=${encodeURIComponent(crop)}` +

          `&quantity_qtl=${quantity}` +

          `&lat=18.5204` +

          `&lon=73.8567` +

          `&horizon=7`

        )

      ]);



    const forecasts =
      forecastData.forecasts || [];


    const byDay = {};


    forecasts.forEach(

      x => {

        byDay[x.day] = x;

      }

    );



    const tamilNaduMarkets =

      (comparisonData || [])
        .filter(
          x =>
            x.state ===
            'Tamil Nadu'
        );



    const best =
      tamilNaduMarkets[0] ||
      comparisonData[0] ||
      {};



    const action =
      String(
        best.action ||
        'SELL NOW'
      ).toUpperCase();



    let recommendationSentence = '';



    if (
      action.includes('WAIT')
    ) {

      const future =
        Number(
          byDay[7]?.predicted_price || 0
        );


      const current =
        Number(
          forecastData.current_price || 0
        );


      const difference =
        future - current;


      recommendationSentence =

        difference > 0

          ? `WAIT: GRAM AI expects ${crop} to improve by approximately ${fmt(difference)} per quintal over the forecast period.`

          : `WAIT: GRAM AI recommends waiting based on the current market trend and expected net realization.`;

    }


    else if (
      action.includes('SHIFT')
    ) {

      recommendationSentence =

        `SHIFT MARKET: ${best.market || 'Another nearby market'} currently provides the strongest expected net income after transport and market charges.`;

    }


    else {

      recommendationSentence =

        `SELL: The current selling opportunity is competitive after transport cost, market charges and forecast movement.`;

    }



    $('forecastResult').innerHTML = `


      <!-- FINAL GRAM AI RECOMMENDATION -->

      <div class="recommendation-main">

        <small>
          ${tr('finalRecommendation')}
        </small>


        <h2>

          ${recommendationSentence}

        </h2>


        <div class="reco-facts">


          <span>

            ${tr('bestMarket')}

            <b>

              ${
                esc(
                  best.market ||
                  forecastData.market?.name ||
                  '—'
                )
              }

            </b>

          </span>



          <span>

            ${tr('expectedNet')}

            <b>

              ${fmt(
                best.net_realizable
              )}

            </b>

          </span>



          <span>

            ${tr('reliability')}

            <b>

              ${num(
                best.predictability_score
              )}%

              ${
                esc(
                  best.predictability_level ||
                  ''
                )
              }

            </b>

          </span>


        </div>

      </div>



      <!-- GRAPHS -->

      <div class="grid chart-grid">


        <div class="card">

          <h3>

            📈 ${tr('priceForecast')}

          </h3>

          <canvas id="priceChart"></canvas>

        </div>



        <div class="card">

          <h3>

            🏆 ${tr('expectedNet')}

          </h3>

          <canvas id="marketChart"></canvas>

        </div>


      </div>



      <!-- 1 / 3 / 7 DAY -->

      <div class="grid stats-4">


        ${card(
          tr('currentPrice'),
          fmt(
            forecastData.current_price
          )
        )}


        ${card(
          tr('predicted1'),
          fmt(
            byDay[1]?.predicted_price
          )
        )}


        ${card(
          tr('predicted3'),
          fmt(
            byDay[3]?.predicted_price
          )
        )}


        ${card(
          tr('predicted7'),
          fmt(
            byDay[7]?.predicted_price
          )
        )}


      </div>



      <!-- MARKET BY MARKET REVIEW -->

      ${section(

        tr('marketPredictions'),

        `

        <div class="table-wrap">

          <table>

            <thead>

              <tr>

                <th>
                  ${tr('market')}
                </th>

                <th>
                  ${tr('distance')}
                </th>

                <th>
                  ${tr('currentPrice')}
                </th>

                <th>
                  7D ${tr('price')}
                </th>

                <th>
                  ${tr('transportCost')}
                </th>

                <th>
                  Market Charge
                </th>

                <th>
                  ${tr('expectedNet')}
                </th>

                <th>
                  ${tr('reliability')}
                </th>

                <th>
                  GRAM AI Review
                </th>

              </tr>

            </thead>


            <tbody>


              ${

                tamilNaduMarkets

                  .map(

                    x => `

                    <tr>


                      <td>

                        <b>
                          ${esc(x.market)}
                        </b>

                      </td>


                      <td>

                        ${num(
                          x.distance_km
                        )} km

                      </td>


                      <td>

                        ${fmt(
                          x.current_price
                        )}

                      </td>


                      <td>

                        ${fmt(
                          x.predicted_price
                        )}

                      </td>


                      <td>

                        ${fmt(
                          x.transport_cost
                        )}

                      </td>


                      <td>

                        ${fmt(
                          x.market_charges
                        )}

                      </td>


                      <td>

                        <b>

                          ${fmt(
                            x.net_realizable
                          )}

                        </b>

                      </td>


                      <td>

                        ${num(
                          x.predictability_score
                        )}%

                      </td>


                      <td>

                        ${marketReviewBadge(
                          x,
                          best
                        )}

                      </td>


                    </tr>

                  `

                  )

                  .join('')

              }


            </tbody>

          </table>

        </div>

        `

      )}


    `;



    /* =========================================
       PRICE GRAPH
    ========================================= */


    const history =
      forecastData.history || [];


    charts.price =
      new Chart(

        $('priceChart'),

        {

          type: 'line',

          data: {

            labels: [

              ...history.map(
                x => x.date
              ),

              '1 Day',

              '3 Days',

              '7 Days'

            ],

            datasets: [

              {

                label:
                  tr('price'),

                data: [

                  ...history.map(
                    x => x.price
                  ),

                  byDay[1]
                    ?.predicted_price,

                  byDay[3]
                    ?.predicted_price,

                  byDay[7]
                    ?.predicted_price

                ]

              }

            ]

          },


          options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

              legend: {

                display: false

              }

            },

            scales: {

              y: {

                ticks: {

                  callback:
                    value =>
                      `₹${Number(
                        value
                      ).toLocaleString(
                        'en-IN'
                      )}`

                }

              }

            }

          }

        }

      );



    /* =========================================
       MARKET NET INCOME GRAPH
    ========================================= */


    const top =
      tamilNaduMarkets
        .slice(0, 6);


    charts.market =
      new Chart(

        $('marketChart'),

        {

          type: 'bar',

          data: {

            labels:

              top.map(

                x =>
                  String(
                    x.market
                  )

                    .replace(
                      ' Central APMC',
                      ''
                    )

                    .replace(
                      ' Regional Mandi',
                      ''
                    )

              ),


            datasets: [

              {

                label:
                  tr('expectedNet'),

                data:

                  top.map(

                    x =>
                      x.net_realizable

                  )

              }

            ]

          },


          options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

              legend: {

                display: false

              }

            },

            scales: {

              y: {

                ticks: {

                  callback:
                    value =>
                      `₹${Number(
                        value
                      ).toLocaleString(
                        'en-IN'
                      )}`

                }

              }

            }

          }

        }

      );


  }

  catch (e) {

    toast(e.message);

  }

}


async function farmerMarket() {

  try {

    const [offers, buyers] = await Promise.all([
      api('/api/v2/v3/offers'),
      api('/api/buyers?state=Tamil Nadu')
    ]);

    $('content').innerHTML = `

      ${section(

        tr('buyerOffers'),

        offers.length

          ? offers.map(o => `

              <div class="offer-card">

                <div class="offer-main">

                  <div>

                    <span class="verified-badge">
                      ✓ ${esc(o.buyer_name)}
                    </span>

                    <h3>
                      ${esc(o.crop)}
                      • ${num(o.quantity_qtl)} qtl
                      @ ${fmt(o.offer_price)}/qtl
                    </h3>

                    <p>
                      ${esc(o.pitch)}
                    </p>

                    <small>
                      ${esc(o.buyer_district)}
                      • Reliability ${num(o.buyer_reliability)}/100
                      • Payment ${num(o.instant_payment)}/100
                    </small>

                  </div>

                  <div class="offer-value">

                    ${fmt(
                      o.offer_price * o.quantity_qtl
                    )}

                  </div>

                </div>


                <div class="action-row">

                  ${button(
                    tr('viewDetails'),
                    `showBuyerDetails(${o.id})`
                  )}


                  ${button(
                    tr('wait'),
                    `offerAction(${o.id},'WAIT')`
                  )}


                  ${button(
                    tr('decline'),
                    `offerAction(${o.id},'DECLINE')`,
                    'danger-btn'
                  )}


                  ${button(
                    tr('accept'),
                    `openOfferConfirmation(${o.id})`,
                    'primary'
                  )}


                  ${button(
                    tr('negotiate'),
                    `openNegotiationChat(${o.id},${o.buyer_user_id},${o.listing_id})`
                  )}


                  ${button(
                    '💬 ' + tr('chat'),
                    `openBuyerChat(${o.buyer_user_id},${o.listing_id})`
                  )}

                </div>

              </div>

            `).join('')

          : `<div class="empty">${tr('noData')}</div>`

      )}


      ${section(

        tr('verifiedBuyers'),

        `

          <div class="buyer-grid">

            ${buyers

              .sort(
                (a,b) =>
                  Number(b.rating || 0) -
                  Number(a.rating || 0)
              )

              .slice(0,8)

              .map(b => `

                <div class="buyer-card">

                  <span class="verified-badge">
                    ✓ Verified
                  </span>

                  <h3>
                    ${esc(b.name)}
                  </h3>

                  <p>
                    ${esc(b.district)}
                    • ${esc(b.crops)}
                  </p>

                  <div class="mini-grid">

                    <span>
                      Rating
                      <b>★ ${b.rating}</b>
                    </span>

                    <span>
                      Payment
                      <b>${b.payment_score}/100</b>
                    </span>

                    <span>
                      Orders
                      <b>${b.completed_orders}</b>
                    </span>

                    <span>
                      Avg pay
                      <b>${b.avg_payment_days} days</b>
                    </span>

                  </div>

                </div>

              `).join('')}

          </div>

        `

      )}

    `;

  }

  catch (e) {

    toast(e.message);

  }

}

async function showBuyerDetails(id){let offers=await api('/api/v2/v3/offers'),o=offers.find(x=>x.id===id);$('modalBody').innerHTML=`<h2>${esc(o.buyer_name)}</h2><div class="profile-summary">${badge(true)}<p><b>Location:</b> ${esc(o.buyer_district)}, ${esc(o.buyer_state)}</p><p><b>Reliability:</b> ${num(o.buyer_reliability)}/100</p><p><b>Instant-payment score:</b> ${num(o.instant_payment)}/100</p><p><b>Cancellation streak:</b> ${o.zero_cancel_streak}</p><p><b>Pitch:</b> ${esc(o.pitch)}</p></div>`;$('modal').classList.remove('hidden')}
async function openOfferConfirmation(id) {

  try {

    /* ---------------------------------------------
       GET THE BUYER OFFER
    --------------------------------------------- */

    const offers =
      await api('/api/v2/v3/offers');


    const o =
      offers.find(
        x => Number(x.id) === Number(id)
      );


    if (!o) {
      throw new Error('Buyer offer not found');
    }


    if (!o.listing_id) {
      throw new Error('Verified crop listing not linked to this offer');
    }



    /* ---------------------------------------------
       GET REAL VERIFIED LISTING DETAILS
    --------------------------------------------- */

    const listing =
      await api(
        `/api/v2/v3/listings/${o.listing_id}`
      );



    /* ---------------------------------------------
       CALCULATIONS
    --------------------------------------------- */

    const offerPrice =
      Number(o.offer_price || 0);


    const quantity =
      Number(o.quantity_qtl || 0);


    const totalOfferValue =
      offerPrice * quantity;


    const farmerAskPrice =
      Number(listing.ask_price || 0);


    const farmerAskTotal =
      farmerAskPrice * quantity;


    const priceDifference =
      offerPrice - farmerAskPrice;


    const tokenAmount =
      Number(
        listing.token_amount ||
        o.token_amount ||
        o.deposit_amount ||
        0
      );


    const transportRate =
      Number(
        listing.transport_cost_per_km ||
        listing.transport_rate_per_km ||
        0
      );


    const qualityConfidenceRaw =
      Number(
        listing.quality_confidence || 0
      );


    const qualityConfidence =
      qualityConfidenceRaw <= 1
        ? qualityConfidenceRaw * 100
        : qualityConfidenceRaw;



    /* ---------------------------------------------
       CONFIRMATION PAGE
    --------------------------------------------- */

    $('content').innerHTML = `

      <div class="offer-confirm-page">


        <!-- BACK -->

        <div class="confirm-topbar">

          <button
            class="secondary"
            onclick="farmerMarket()"
          >
            ← Back to Market & Offers
          </button>

        </div>



        <div class="confirm-card">


          <!-- HEADER -->

          <div class="confirm-header">

            <div>

              <span class="verified-badge">
                ✓ Verified Buyer
              </span>

              <h2>
                Confirm Buyer Offer
              </h2>

              <p>
                Review the verified crop, buyer offer,
                transport and token details before accepting.
              </p>

            </div>


            <div class="confirm-icon">
              🤝
            </div>

          </div>



          <!-- BUYER DETAILS -->

          <div class="confirm-buyer">


            <div class="buyer-avatar">

              ${esc(
                String(
                  o.buyer_name || 'B'
                )
                  .charAt(0)
                  .toUpperCase()
              )}

            </div>


            <div class="confirm-buyer-info">

              <span class="small-label">
                Buyer
              </span>

              <h3>
                ${esc(o.buyer_name)}
              </h3>

              <p>
                📍 ${esc(
                  o.buyer_district ||
                  'Tamil Nadu'
                )}
                ${
                  o.buyer_state
                    ? `, ${esc(o.buyer_state)}`
                    : ', Tamil Nadu'
                }
              </p>

            </div>


            <div class="buyer-trust">

              <span>
                Reliability
              </span>

              <b>
                ${num(o.buyer_reliability)}/100
              </b>

            </div>


            <div class="buyer-trust">

              <span>
                Payment Score
              </span>

              <b>
                ${num(o.instant_payment)}/100
              </b>

            </div>


          </div>



          <!-- VERIFIED PRODUCE -->

          <div class="confirm-section-title">

            <div>

              <h3>
                🌾 Verified Produce Details
              </h3>

              <p>
                Information taken directly from your
                GRAM AI verified listing.
              </p>

            </div>


            ${
              listing.gram_verified

                ? `
                  <span class="verified-badge">
                    ✓ GRAM AI Verified
                  </span>
                `

                : `
                  <span class="tag">
                    Verification record
                  </span>
                `
            }

          </div>



          <div class="confirm-detail-grid">


            <div class="confirm-detail">

              <small>
                Crop
              </small>

              <b>
                ${esc(listing.crop || o.crop)}
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Variety
              </small>

              <b>
                ${esc(listing.variety || '—')}
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                GRAM AI Quality Grade
              </small>

              <b class="confirm-grade">
                Grade ${esc(listing.grade || '—')}
              </b>

              ${
                qualityConfidence > 0
                  ? `
                    <span>
                      ${num(qualityConfidence)}% confidence
                    </span>
                  `
                  : ''
              }

            </div>



            <div class="confirm-detail">

              <small>
                Buyer Requested Quantity
              </small>

              <b>
                ${num(quantity)} qtl
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Available Quantity
              </small>

              <b>
                ${num(
                  listing.quantity_qtl ||
                  listing.available_quantity_qtl ||
                  0
                )} qtl
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Harvest Date
              </small>

              <b>
                ${esc(
                  listing.harvest_date ||
                  listing.expected_harvest_date ||
                  '—'
                )}
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Packaging
              </small>

              <b>
                ${esc(
                  listing.packaging ||
                  '—'
                )}
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Farmer Location
              </small>

              <b>
                ${esc(
                  listing.district ||
                  me.district ||
                  'Tamil Nadu'
                )},
                Tamil Nadu
              </b>

            </div>


          </div>



          <!-- PRICE COMPARISON -->

          <div class="confirm-section-title">

            <div>

              <h3>
                💰 Price & Offer Details
              </h3>

              <p>
                Compare your listed price against the buyer offer.
              </p>

            </div>

          </div>



          <div class="confirm-price-grid">


            <div class="price-box">

              <small>
                Your Ask Price
              </small>

              <b>
                ${fmt(farmerAskPrice)}
                <span>/ qtl</span>
              </b>

            </div>



            <div class="price-arrow">
              →
            </div>



            <div class="price-box buyer-offer-price">

              <small>
                Buyer Offer
              </small>

              <b>
                ${fmt(offerPrice)}
                <span>/ qtl</span>
              </b>

            </div>


          </div>



          <div class="confirm-detail-grid compact">


            <div class="confirm-detail">

              <small>
                Your Listed Value
              </small>

              <b>
                ${fmt(farmerAskTotal)}
              </b>

            </div>



            <div class="confirm-detail highlight-detail">

              <small>
                Buyer Offer Value
              </small>

              <b>
                ${fmt(totalOfferValue)}
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Price Difference / qtl
              </small>

              <b class="${
                priceDifference >= 0
                  ? 'positive-price'
                  : 'negative-price'
              }">

                ${
                  priceDifference >= 0
                    ? '+'
                    : ''
                }

                ${fmt(priceDifference)}

              </b>

            </div>


          </div>



          <!-- TRANSPORT -->

          <div class="confirm-section-title">

            <div>

              <h3>
                🚚 Transport Details
              </h3>

            </div>

          </div>



          <div class="confirm-detail-grid">


            <div class="confirm-detail">

              <small>
                Seller Transport
              </small>

              <b>
                ${
                  listing.seller_transport
                    ? '✓ Available'
                    : 'Buyer pickup / self arranged'
                }
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Transport Rate
              </small>

              <b>
                ${
                  listing.seller_transport

                    ? `${fmt(transportRate)} / km`

                    : '—'
                }
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Delivery Radius
              </small>

              <b>
                ${
                  listing.delivery_radius_km
                    ? `${num(listing.delivery_radius_km)} km`
                    : '—'
                }
              </b>

            </div>



            <div class="confirm-detail">

              <small>
                Loading Included
              </small>

              <b>
                ${
                  listing.loading_included
                    ? '✓ Yes'
                    : 'No'
                }
              </b>

            </div>


          </div>



          <!-- TOKEN -->

          <div class="confirm-token-card">


            <div class="confirm-token-icon">
              🔐
            </div>


            <div>

              <small>
                Required Secure Token
              </small>

              <h2>
                ${fmt(tokenAmount)}
              </h2>

              <p>
                Buyer must complete this payment before
                the accepted order becomes confirmed.
              </p>

            </div>


            <span class="await-token-badge">
              Awaiting Token After Acceptance
            </span>


          </div>



          <!-- BUYER PITCH -->

          <div class="buyer-pitch-box">

            <small>
              💬 Buyer Message
            </small>

            <p>
              ${esc(
                o.pitch ||
                'No buyer message was provided.'
              )}
            </p>

          </div>



          <!-- YOLO CERTIFICATE -->

          <div class="certificate-confirm-box">


            <div>

              <span class="certificate-icon">
                📄
              </span>

              <div>

                <b>
                  GRAM AI Quality Certificate
                </b>

                <p>
                  Review the crop quality certificate generated
                  from the verified produce inspection.
                </p>

              </div>

            </div>


            ${
              listing.certificate_url

                ? `

                  <button
                    class="secondary"
                    onclick="openCertificate(
                      '${listing.certificate_url}'
                    )"
                  >
                    View Certificate
                  </button>

                `

                : `

                  <span class="tag">
                    Certificate unavailable
                  </span>

                `
            }


          </div>



          <!-- SECURITY -->

          <div class="token-rule-box">

            <b>
              🔒 GRAM AI Secure Acceptance Rule
            </b>

            <p>

              Clicking <strong>Confirm & Accept Offer</strong>
              records your acceptance and notifies the buyer.

              The order remains
              <strong>AWAITING TOKEN</strong>
              until the required secure token is paid.

            </p>

          </div>



          <!-- FINAL BUTTONS -->

          <div class="confirm-actions">


            <button
              class="secondary"
              onclick="farmerMarket()"
            >
              Cancel
            </button>


            <button
              class="primary confirm-btn"
              onclick="confirmOfferAcceptance(${o.id})"
            >
              ✓ Confirm & Accept Offer
            </button>


          </div>


        </div>


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}

async function offerAction(id,a){try{await api(`/api/v2/v3/offers/${id}`,{method:'PATCH',body:JSON.stringify({action:a})});toast(a);farmerMarket()}catch(e){toast(e.message)}}
async function confirmOfferAcceptance(id) {

  try {

    const d = await api(

      `/api/v2/v3/offers/${id}`,

      {

        method: 'PATCH',

        body: JSON.stringify({

          action: 'ACCEPT'

        })

      }

    );


    $('content').innerHTML = `

      <div class="accept-success-page">


        <div class="accept-success-card">


          <div class="big-success-tick">

            ✓

          </div>


          <h2>
            Offer Accepted Successfully
          </h2>


          <p>

            The buyer has been notified that
            you accepted the offer.

          </p>


          <div class="success-status-box">
          <div class="success-small-tick">
          ✓
          </div>
          
          <div>
          <span>
          
            Farmer Acceptance Recorded
            </span>

    <b>
      AWAITING TOKEN PAYMENT
    </b>

  </div>

</div>


          <p class="soft-note">

            The transaction becomes confirmed
            after the buyer completes the required
            secure token payment.

          </p>


          <div class="action-row">


            <button
              class="secondary"
              onclick="farmerMarket()"
            >

              Back to Offers

            </button>


            <button
              class="primary"
              onclick="route('chats')"
            >

              💬 Message Buyer

            </button>


          </div>


        </div>


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}
async function openNegotiationChat(
  offerId,
  buyerId,
  listingId
) {

  try {

    const offers =
      await api('/api/v2/v3/offers');


    const o =
      offers.find(
        x => Number(x.id) === Number(offerId)
      );


    if (!o) {

      throw new Error(
        'Offer not found'
      );

    }


    await ensureChatWithBuyer(
      buyerId,
      listingId,
      null,
      `Regarding your offer for ${o.crop}`
    );


    localStorage.setItem(
      'gram_open_chat_user',
      String(buyerId)
    );


    localStorage.setItem(
      'gram_open_chat_listing',
      String(listingId || '')
    );


    localStorage.setItem(
      'gram_negotiation_offer',
      String(offerId)
    );


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}

async function startChat(
  other,
  listing = null,
  pre = null
) {

  await openBuyerChat(
    other,
    listing,
    pre
  );

}

async function openBuyerChat(
  buyerId,
  listingId = null,
  preorderId = null
) {

  try {

    await ensureChatWithBuyer(
      buyerId,
      listingId,
      preorderId
    );


    localStorage.setItem(
      'gram_open_chat_user',
      String(buyerId)
    );


    localStorage.setItem(
      'gram_open_chat_listing',
      String(listingId || '')
    );


    localStorage.removeItem(
      'gram_negotiation_offer'
    );


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}

async function ensureChatWithBuyer(
  otherUserId,
  listingId = null,
  preorderId = null,
  firstMessage = null
) {

  const threads =
    await api('/api/v2/v3/chats');


  const existing =
    threads.find(

      t =>

        Number(
          t.farmer_id === me.id
            ? t.buyer_id
            : t.farmer_id
        ) === Number(otherUserId)

        &&

        (
          !listingId ||
          Number(t.listing_id) ===
          Number(listingId)
        )

    );


  if (existing) {

    localStorage.setItem(
      'gram_open_thread',
      String(existing.id)
    );

    return existing;

  }


  if (firstMessage) {

    await api(

      '/api/v2/v3/chats',

      {

        method: 'POST',

        body: JSON.stringify({

          other_user_id:
            Number(otherUserId),

          message:
            firstMessage,

          listing_id:
            listingId,

          preorder_id:
            preorderId

        })

      }

    );


    const newThreads =
      await api('/api/v2/v3/chats');


    const created =
      newThreads.find(

        t =>

          Number(
            t.farmer_id === me.id
              ? t.buyer_id
              : t.farmer_id
          ) === Number(otherUserId)

      );


    if (created) {

      localStorage.setItem(
        'gram_open_thread',
        String(created.id)
      );

    }


    return created;

  }


  return null;

}


async function farmerPreorders() {

  try {

    const [demands, linkedPreorders] =
      await Promise.all([
        api('/api/v2/v3/buyer-preorders/available'),
        api('/api/v2/preorders?state=Tamil Nadu')
      ]);


    const incoming =
      Array.isArray(demands)
        ? demands
        : [];


    const accepted =
      Array.isArray(linkedPreorders)
        ? linkedPreorders
        : [];


    $('content').innerHTML = `

      <div class="preorder-marketplace-page">


        <div class="hero-reco">

          <div>

            <small>
              BUYER DEMAND MARKETPLACE
            </small>

            <h2>
              Buyers are looking for upcoming harvests
            </h2>

            <p>
              Review requirements and choose whether
              you want to supply, negotiate or decline.
              Your crop is never reserved until the
              buyer completes the secure token payment.
            </p>

          </div>

          <div>
            <span class="verified-badge">
              ${incoming.length} Open Requirement${incoming.length === 1 ? '' : 's'}
            </span>
          </div>

        </div>


        ${section(
          '🔔 New Buyer Requirements',

          incoming.length

          ? `

            <div class="harvest-grid">

              ${incoming.map(d => {

                const response =
                  String(
                    d.farmer_response || ''
                  ).toUpperCase();

                return `

                  <div class="preorder-card">


                    <div class="harvest-top">

                      <div>

                        <span class="crop-icon">
                          🛒
                        </span>

                        <b>
                          ${esc(d.crop)}
                          •
                          ${esc(d.variety || 'Any variety')}
                        </b>

                      </div>


                      <span class="tag ${
                        response === 'ACCEPT'
                          ? 'success'
                          : ''
                      }">

                        ${
                          response
                            ? esc(response)
                            : 'NEW REQUEST'
                        }

                      </span>

                    </div>


                    <p>

                      Buyer:
                      <b>
                        ${esc(d.buyer_name || 'Verified Buyer')}
                      </b>

                      •

                      ${esc(
                        d.delivery_district
                        || d.buyer_home_district
                        || ''
                      )},

                      ${esc(
                        d.delivery_state
                        || 'Tamil Nadu'
                      )}

                    </p>


                    <div class="mini-grid">

                      <span>
                        Required
                        <b>
                          ${num(d.quantity_qtl)} qtl
                        </b>
                      </span>

                      <span>
                        Still Required
                        <b>
                          ${num(d.remaining_quantity_qtl)} qtl
                        </b>
                      </span>

                      <span>
                        Buyer Offer
                        <b>
                          ${fmt(d.offer_price)}/qtl
                        </b>
                      </span>

                      <span>
                        Grade Required
                        <b>
                          ${esc(d.grade_required || 'Any')}
                        </b>
                      </span>

                      <span>
                        Required By
                        <b>
                          ${esc(d.required_by_date)}
                        </b>
                      </span>

                      <span>
                        Token Offered
                        <b>
                          ${fmt(d.token_offer)}
                        </b>
                      </span>

                      <span>
                        Delivery
                        <b>
                          ${preorderDeliveryLabel(d.delivery_mode)}
                        </b>
                      </span>

                      <span>
                        Buyer Reliability
                        <b>
                          ${num(
                            d.buyer_reliability_score
                            || d.buyer_reliability
                            || 0
                          )}/100
                        </b>
                      </span>

                    </div>


                    <div class="ai-note">

                      <b>GRAM AI Market Outlook:</b>

                      1d ${fmt(d.predicted_1d)}
                      •

                      3d ${fmt(d.predicted_3d)}
                      •

                      7d ${fmt(d.predicted_7d)}

                      •

                      Confidence:
                      ${esc(d.forecast_confidence || '—')}

                    </div>


                    ${
                      d.special_requirements

                      ? `

                        <div class="info-panel">

                          <b>
                            Buyer Requirements
                          </b>

                          <p>
                            ${esc(d.special_requirements)}
                          </p>

                        </div>

                      `

                      : ''
                    }


                    <div class="action-row">


                      <button
                        class="primary"
                        onclick="
                          openFarmerBuyerDemand(${d.id})
                        "
                      >
                        👁 View & Respond
                      </button>


                      <button
                        class="secondary"
                        onclick="
                          openPreorderDemandChat(
                            ${d.buyer_id},
                            ${d.id},
                            false
                          )
                        "
                      >
                        💬 Chat
                      </button>


                      <button
                        class="secondary"
                        onclick="
                          openPreorderDemandChat(
                            ${d.buyer_id},
                            ${d.id},
                            true
                          )
                        "
                      >
                        🤝 Negotiate
                      </button>


                    </div>


                  </div>

                `;

              }).join('')}

            </div>

          `

          : `

            <div class="empty">

              No open buyer requirements currently
              match your Tamil Nadu farmer profile.

            </div>

          `
        )}


        ${section(
          '🔒 My Accepted / Active Pre-Orders',

          accepted.length

          ? accepted.map(p => `

              <div class="preorder-card">


                <div>

                  <span class="tag">
                    ${esc(p.status)}
                  </span>

                  <h3>
                    ${esc(p.crop || 'Harvest')}
                    •
                    ${num(p.quantity_qtl)} qtl
                  </h3>

                  <p>

                    Buyer:
                    <b>
                      ${esc(p.buyer_name || 'Buyer')}
                    </b>

                    •

                    Offer:
                    ${fmt(p.offer_price)}/qtl

                  </p>


                  <div class="mini-grid">

                    <span>
                      1 Day
                      <b>${fmt(p.predicted_1d)}</b>
                    </span>

                    <span>
                      3 Days
                      <b>${fmt(p.predicted_3d)}</b>
                    </span>

                    <span>
                      7 Days
                      <b>${fmt(p.predicted_7d)}</b>
                    </span>

                    <span>
                      Token
                      <b>${fmt(p.deposit_amount)}</b>
                    </span>

                    <span>
                      Token Status
                      <b>
                        ${esc(
                          p.token_payment_status
                          || 'UNPAID'
                        )}
                      </b>
                    </span>

                    <span>
                      GRAM AI
                      <b>
                        ${esc(
                          p.recommended_action
                          || '—'
                        )}
                      </b>
                    </span>

                  </div>

                </div>


                <div class="action-row">

                  <button
                    class="secondary"
                    onclick="
                      openPreorderDemandChat(
                        ${p.buyer_id},
                        ${p.buyer_demand_id || p.id},
                        false
                      )
                    "
                  >
                    💬 Buyer Chat
                  </button>

                </div>


              </div>

            `).join('')

          : `

              <div class="empty">

                You have not accepted any buyer
                pre-orders yet.

              </div>

            `
        )}


      </div>

    `;


  }

  catch (e) {

    $('content').innerHTML = `

      <div class="card error">
        ${esc(e.message)}
      </div>

    `;

  }

}

async function farmerPreorders() {

  try {

    const [demands, linkedPreorders] =
      await Promise.all([
        api('/api/v2/v3/buyer-preorders/available'),
        api('/api/v2/preorders?state=Tamil Nadu')
      ]);


    const incoming =
      Array.isArray(demands)
        ? demands
        : [];


    const accepted =
      Array.isArray(linkedPreorders)
        ? linkedPreorders
        : [];


    $('content').innerHTML = `

      <div class="preorder-marketplace-page">


        <div class="hero-reco">

          <div>

            <small>
              BUYER DEMAND MARKETPLACE
            </small>

            <h2>
              Buyers are looking for upcoming harvests
            </h2>

            <p>
              Review requirements and choose whether
              you want to supply, negotiate or decline.
              Your crop is never reserved until the
              buyer completes the secure token payment.
            </p>

          </div>

          <div>
            <span class="verified-badge">
              ${incoming.length} Open Requirement${incoming.length === 1 ? '' : 's'}
            </span>
          </div>

        </div>


        ${section(
          '🔔 New Buyer Requirements',

          incoming.length

          ? `

            <div class="harvest-grid">

              ${incoming.map(d => {

                const response =
                  String(
                    d.farmer_response || ''
                  ).toUpperCase();

                return `

                  <div class="preorder-card">


                    <div class="harvest-top">

                      <div>

                        <span class="crop-icon">
                          🛒
                        </span>

                        <b>
                          ${esc(d.crop)}
                          •
                          ${esc(d.variety || 'Any variety')}
                        </b>

                      </div>


                      <span class="tag ${
                        response === 'ACCEPT'
                          ? 'success'
                          : ''
                      }">

                        ${
                          response
                            ? esc(response)
                            : 'NEW REQUEST'
                        }

                      </span>

                    </div>


                    <p>

                      Buyer:
                      <b>
                        ${esc(d.buyer_name || 'Verified Buyer')}
                      </b>

                      •

                      ${esc(
                        d.delivery_district
                        || d.buyer_home_district
                        || ''
                      )},

                      ${esc(
                        d.delivery_state
                        || 'Tamil Nadu'
                      )}

                    </p>


                    <div class="mini-grid">

                      <span>
                        Required
                        <b>
                          ${num(d.quantity_qtl)} qtl
                        </b>
                      </span>

                      <span>
                        Still Required
                        <b>
                          ${num(d.remaining_quantity_qtl)} qtl
                        </b>
                      </span>

                      <span>
                        Buyer Offer
                        <b>
                          ${fmt(d.offer_price)}/qtl
                        </b>
                      </span>

                      <span>
                        Grade Required
                        <b>
                          ${esc(d.grade_required || 'Any')}
                        </b>
                      </span>

                      <span>
                        Required By
                        <b>
                          ${esc(d.required_by_date)}
                        </b>
                      </span>

                      <span>
                        Token Offered
                        <b>
                          ${fmt(d.token_offer)}
                        </b>
                      </span>

                      <span>
                        Delivery
                        <b>
                          ${preorderDeliveryLabel(d.delivery_mode)}
                        </b>
                      </span>

                      <span>
                        Buyer Reliability
                        <b>
                          ${num(
                            d.buyer_reliability_score
                            || d.buyer_reliability
                            || 0
                          )}/100
                        </b>
                      </span>

                    </div>


                    <div class="ai-note">

                      <b>GRAM AI Market Outlook:</b>

                      1d ${fmt(d.predicted_1d)}
                      •

                      3d ${fmt(d.predicted_3d)}
                      •

                      7d ${fmt(d.predicted_7d)}

                      •

                      Confidence:
                      ${esc(d.forecast_confidence || '—')}

                    </div>


                    ${
                      d.special_requirements

                      ? `

                        <div class="info-panel">

                          <b>
                            Buyer Requirements
                          </b>

                          <p>
                            ${esc(d.special_requirements)}
                          </p>

                        </div>

                      `

                      : ''
                    }


                    <div class="action-row">


                      <button
                        class="primary"
                        onclick="
                          openFarmerBuyerDemand(${d.id})
                        "
                      >
                        👁 View & Respond
                      </button>


                      <button
                        class="secondary"
                        onclick="
                          openPreorderDemandChat(
                            ${d.buyer_id},
                            ${d.id},
                            false
                          )
                        "
                      >
                        💬 Chat
                      </button>


                      <button
                        class="secondary"
                        onclick="
                          openPreorderDemandChat(
                            ${d.buyer_id},
                            ${d.id},
                            true
                          )
                        "
                      >
                        🤝 Negotiate
                      </button>


                    </div>


                  </div>

                `;

              }).join('')}

            </div>

          `

          : `

            <div class="empty">

              No open buyer requirements currently
              match your Tamil Nadu farmer profile.

            </div>

          `
        )}


        ${section(
          '🔒 My Accepted / Active Pre-Orders',

          accepted.length

          ? accepted.map(p => `

              <div class="preorder-card">


                <div>

                  <span class="tag">
                    ${esc(p.status)}
                  </span>

                  <h3>
                    ${esc(p.crop || 'Harvest')}
                    •
                    ${num(p.quantity_qtl)} qtl
                  </h3>

                  <p>

                    Buyer:
                    <b>
                      ${esc(p.buyer_name || 'Buyer')}
                    </b>

                    •

                    Offer:
                    ${fmt(p.offer_price)}/qtl

                  </p>


                  <div class="mini-grid">

                    <span>
                      1 Day
                      <b>${fmt(p.predicted_1d)}</b>
                    </span>

                    <span>
                      3 Days
                      <b>${fmt(p.predicted_3d)}</b>
                    </span>

                    <span>
                      7 Days
                      <b>${fmt(p.predicted_7d)}</b>
                    </span>

                    <span>
                      Token
                      <b>${fmt(p.deposit_amount)}</b>
                    </span>

                    <span>
                      Token Status
                      <b>
                        ${esc(
                          p.token_payment_status
                          || 'UNPAID'
                        )}
                      </b>
                    </span>

                    <span>
                      GRAM AI
                      <b>
                        ${esc(
                          p.recommended_action
                          || '—'
                        )}
                      </b>
                    </span>

                  </div>

                </div>


                <div class="action-row">

                  <button
                    class="secondary"
                    onclick="
                      openPreorderDemandChat(
                        ${p.buyer_id},
                        ${p.buyer_demand_id || p.id},
                        false
                      )
                    "
                  >
                    💬 Buyer Chat
                  </button>

                </div>


              </div>

            `).join('')

          : `

              <div class="empty">

                You have not accepted any buyer
                pre-orders yet.

              </div>

            `
        )}


      </div>

    `;


  }

  catch (e) {

    $('content').innerHTML = `

      <div class="card error">
        ${esc(e.message)}
      </div>

    `;

  }

}

function preorderDeliveryLabel(mode) {

  const labels = {

    BUYER_PICKUP:
      'Buyer Pickup',

    FARMER_TRANSPORT:
      'Farmer Transport',

    FLEXIBLE:
      'Flexible'

  };


  return labels[
    String(mode || '').toUpperCase()
  ] || 'Flexible';

}

async function submitFarmerDemandResponse(
  demandId,
  action
) {

  try {

    const harvestId =
      Number(
        $('farmerDemandHarvest')?.value
        || 0
      );


    const qty =
      Number(
        $('farmerDemandQty')?.value
        || 0
      );


    const price =
      Number(
        $('farmerDemandPrice')?.value
        || 0
      );


    const message =
      $('farmerDemandMessage')?.value
        ?.trim()
      || '';


    if (action === 'ACCEPT') {

      if (!harvestId) {

        throw new Error(
          'Select the harvest you want to use for this buyer requirement'
        );

      }


      if (!qty || qty <= 0) {

        throw new Error(
          'Enter the quantity you can supply'
        );

      }

    }


    if (
      action === 'NEGOTIATE'
      &&
      (!price || price <= 0)
    ) {

      throw new Error(
        'Enter your counter price'
      );

    }


    const body = {

      action,

      harvest_id:
        harvestId || null,

      quantity_qtl:
        qty > 0
          ? qty
          : null,

      counter_price:
        price > 0
          ? price
          : null,

      message

    };


    const result =
      await api(

        `/api/v2/v3/buyer-preorders/${demandId}/farmer-response`,

        {

          method: 'PATCH',

          body: JSON.stringify(
            body
          )

        }

      );


    if (action === 'ACCEPT') {

      closeModal();


      $('content').innerHTML = `

        <div class="order-success-page">

          <div class="order-success-card">

            <div class="success-tick">
              ✓
            </div>

            <span class="verified-badge">
              Supply Offer Accepted
            </span>

            <h2>
              Buyer Notified
            </h2>

            <p>
              You agreed to supply this buyer.
              The crop has NOT been reserved yet.
            </p>

            <div class="info-panel">

              🔐 Buyer must now pay the secure
              booking token

              <b>
                ${fmt(result.token_required)}
              </b>

              before your harvest quantity is
              reserved.

            </div>

            <div class="action-row">

              <button
                class="primary"
                onclick="farmerPreorders()"
              >
                Back to Pre-Orders
              </button>

            </div>

          </div>

        </div>

      `;


      return;

    }


    if (action === 'NEGOTIATE') {

      closeModal();


      await openPreorderDemandChat(
        null,
        demandId,
        true
      );


      return;

    }


    toast(
      action === 'DECLINE'
        ? 'Buyer requirement declined'
        : 'Response sent to buyer'
    );


    closeModal();

    farmerPreorders();


  }

  catch (e) {

    toast(e.message);

  }

}




async function farmerTransport() {

  try {

    const [my, t, g] = await Promise.all([

      api('/api/v2/v3/transports'),

      api('/api/transport?state=Tamil Nadu'),

      api('/api/v2/groups?state=Tamil Nadu')

    ]);


    $('content').innerHTML = `


      ${section(

        tr('myTransport'),

        my.length

          ? my.map(x => `

              <div class="list-item">

                <div>

                  <b>
                    ${esc(x.crop || 'Crop')}
                    •
                    ${esc(x.pickup)}
                    →
                    ${esc(x.dropoff)}
                  </b>

                  <small>
                    ${num(x.distance_km)} km
                    •
                    ${x.shared ? 'Shared route' : 'Dedicated'}
                    •
                    ${esc(x.status)}
                  </small>

                </div>


                <b>
                  ${fmt(x.quoted_cost)}
                </b>

              </div>

            `).join('')

          : `

              <div class="empty">
                No transport booked yet.
              </div>

            `,

        button(
          '＋ Request Transport',
          'openTransportRequest()',
          'primary'
        )

      )}



      ${section(

        tr('sharedTransport'),

        `

          <div class="transport-grid">

            ${t.slice(0, 8).map(x => `

              <div class="transport-card">

                <h3>
                  ${esc(x.name)}
                </h3>


                <p>
                  ${esc(x.vehicle_type)}
                  •
                  ${num(x.capacity_qtl)} qtl
                </p>


                <div>

                  ₹${num(x.rate_per_km)}/km

                  •

                  ★ ${num(x.rating)}

                  •

                  GPS
                  ${x.gps_enabled ? '✓' : '—'}

                </div>

              </div>

            `).join('')}

          </div>

        `

      )}



      ${section(

        tr('groupSelling'),

        `

          <div class="group-intro">

            <div>

              <h3>
                👥 Sell Together. Earn Better.
              </h3>

              <p>
                Combine produce with nearby farmers,
                attract bulk buyers and reduce transport
                costs through collective selling.
              </p>

            </div>


            <div class="group-action-row">

              <button
                class="primary"
                onclick="openGroupSellingPage()"
              >
                👥 Create / Join Selling Group
              </button>

            </div>

          </div>



          <div class="existing-groups">


            <div class="group-list-heading">

              <div>

                <h3>
                  Available Selling Groups
                </h3>

                <p>
                  View farmer groups currently available
                  in Tamil Nadu.
                </p>

              </div>

            </div>



            ${

              g.length

                ? g.map(x => `

                    <div class="list-item group-list-item">


                      <div>

                        <b>
                          ${esc(x.name)}
                        </b>


                        <small>

                          ${esc(x.crop)}

                          •

                          ${esc(x.district)}

                          •

                          ${esc(x.state)}

                        </small>

                      </div>


                      <span class="tag">

                        ${esc(x.status || 'OPEN')}

                      </span>


                    </div>

                  `).join('')


                : `

                    <div class="empty">

                      No selling groups available yet.

                      Create the first group or join one
                      using a group code.

                    </div>

                  `

            }


          </div>

        `

      )}


    `;


  }

  catch (e) {

    toast(e.message);

  }

}

function openTransportRequest(){$('modalBody').innerHTML=`<h2>Request Transport</h2><div class="form-grid"><div class="field"><label>Crop</label><input id="trCrop" class="control" value="Tomato"></div><div class="field"><label>Pickup</label><input id="trPick" class="control" value="Coimbatore Farm"></div><div class="field"><label>Drop</label><input id="trDrop" class="control" value="Coimbatore APMC"></div><div class="field"><label>Distance km</label><input id="trKm" class="control" type="number" value="22"></div><div class="field"><label>Estimated cost ₹</label><input id="trCost" class="control" type="number" value="500"></div><div class="field"><label><input id="trShared" type="checkbox" checked> Shared route</label></div></div><button class="primary wide" onclick="saveTransport()">Submit</button>`;$('modal').classList.remove('hidden')}
async function saveTransport(){try{await api('/api/v2/v3/transports',{method:'POST',body:JSON.stringify({crop:$('trCrop').value,pickup:$('trPick').value,dropoff:$('trDrop').value,distance_km:+$('trKm').value,quoted_cost:+$('trCost').value,shared:$('trShared').checked})});closeModal();farmerTransport()}catch(e){toast(e.message)}}
async function openGroupSellingPage() {

  try {

    $('content').innerHTML = `

      <div class="selling-group-page">


        <div class="group-page-head">

          <button
            class="secondary"
            onclick="farmerTransport()"
          >
            ← Back to Transport & Groups
          </button>


          <div>

            <h2>
              👥 Group Selling
            </h2>

            <p>
              Combine produce with nearby farmers,
              attract bulk buyers and reduce transport cost.
            </p>

          </div>

        </div>



        <div class="group-choice-grid">


          <!-- CREATE -->

          <div class="group-choice-card">

            <div class="group-choice-icon">
              🌾
            </div>

            <h3>
              Create New Selling Group
            </h3>

            <p>
              Create your own farmer group.
              You will become the group owner and receive a
              unique joining code.
            </p>

            <button
              class="primary wide"
              onclick="showCreateGroupForm()"
            >
              Create New Group
            </button>

          </div>



          <!-- JOIN -->

          <div class="group-choice-card">

            <div class="group-choice-icon">
              🔑
            </div>

            <h3>
              Join Existing Group
            </h3>

            <p>
              Enter the joining code shared by another farmer.
              Your request will be sent to the group owner.
            </p>

            <button
              class="secondary wide"
              onclick="showJoinGroupForm()"
            >
              Join Using Code
            </button>

          </div>


        </div>


        <div id="groupFormArea"></div>


        <div id="mySellingGroups"></div>


      </div>

    `;


    await loadMySellingGroups();


  }

  catch (e) {

    toast(e.message);

  }

}
function showCreateGroupForm() {

  $('groupFormArea').innerHTML = `

    <div class="group-form-card">

      <div class="group-form-title">

        <div>

          <h3>
            🌱 Create Selling Group
          </h3>

          <p>
            Add the details farmers and buyers should see.
          </p>

        </div>

      </div>


      <div class="form-grid">


        <div class="field">

          <label>
            Group Name
          </label>

          <input
            id="sgName"
            class="control"
            placeholder="Example: Coimbatore Tomato Farmers"
          >

        </div>


        <div class="field">

          <label>
            Main Crop
          </label>

          <input
            id="sgCrop"
            class="control"
            value="Tomato"
          >

        </div>


        <div class="field">

          <label>
            District
          </label>

          <input
            id="sgDistrict"
            class="control"
            value="${esc(me.district || 'Coimbatore')}"
          >

        </div>


        <div class="field">

          <label>
            Village / Area
          </label>

          <input
            id="sgArea"
            class="control"
            placeholder="Example: Baramati"
          >

        </div>


        <div class="field">

          <label>
            Your Quantity (qtl)
          </label>

          <input
            id="sgQuantity"
            class="control"
            type="number"
            value="10"
            min="1"
          >

        </div>


        <div class="field">

          <label>
            Target Group Quantity (qtl)
          </label>

          <input
            id="sgTarget"
            class="control"
            type="number"
            value="100"
            min="1"
          >

        </div>


        <div class="field">

          <label>
            Expected Price / qtl
          </label>

          <input
            id="sgPrice"
            class="control"
            type="number"
            value="2400"
            min="1"
          >

        </div>


        <div class="field">

          <label>
            Expected Harvest Date
          </label>

          <input
            id="sgDate"
            class="control"
            type="date"
          >

        </div>


        <div class="field full">

          <label>
            Group Description
          </label>

          <textarea
            id="sgDescription"
            class="control"
            rows="3"
            placeholder="Example: Farmers combining Grade A tomato harvest for bulk buyers."
          ></textarea>

        </div>


        <div class="field">

          <label>
            Shared Transport
          </label>

          <select
            id="sgTransport"
            class="control"
          >

            <option value="true">
              Yes — Share Transport
            </option>

            <option value="false">
              No
            </option>

          </select>

        </div>


        <div class="field">

          <label>
            Maximum Members
          </label>

          <input
            id="sgMaxMembers"
            class="control"
            type="number"
            value="20"
            min="2"
          >

        </div>


      </div>


      <div class="group-form-actions">

        <button
          class="secondary"
          onclick="$('groupFormArea').innerHTML=''"
        >
          Cancel
        </button>


        <button
          class="primary"
          onclick="submitSellingGroup()"
        >
          ✓ Create Group
        </button>

      </div>

    </div>

  `;

}

async function submitSellingGroup() {

  try {

    const name =
      $('sgName').value.trim();


    const crop =
      $('sgCrop').value.trim();


    const district =
      $('sgDistrict').value.trim();


    const area =
      $('sgArea').value.trim();


    const quantity =
      Number($('sgQuantity').value);


    const target =
      Number($('sgTarget').value);


    const price =
      Number($('sgPrice').value);


    const date =
      $('sgDate').value;


    const description =
      $('sgDescription').value.trim();


    const sharedTransport =
      $('sgTransport').value === 'true';


    const maxMembers =
      Number($('sgMaxMembers').value);



    if (!name) {

      throw new Error(
        'Enter group name'
      );

    }


    if (!crop) {

      throw new Error(
        'Enter crop'
      );

    }


    if (!district) {

      throw new Error(
        'Enter district'
      );

    }


    if (!quantity || quantity <= 0) {

      throw new Error(
        'Enter your available quantity'
      );

    }


    if (!target || target < quantity) {

      throw new Error(
        'Target quantity must be at least your quantity'
      );

    }


    const result =
      await api(

        '/api/v2/groups',

        {

          method: 'POST',

          body: JSON.stringify({

            name: name,

            crop: crop,

            district: district,

            state: 'Tamil Nadu',

            area: area,

            quantity_qtl: quantity,

            target_quantity_qtl: target,

            expected_price: price,

            expected_harvest_date: date || null,

            description: description,

            shared_transport: sharedTransport,

            max_members: maxMembers

          })

        }

      );


    toast(
      'Selling group created successfully'
    );


    showGroupCreatedSuccess(result);


  }

  catch (e) {

    toast(e.message);

  }

}
function showGroupCreatedSuccess(group) {

  const joinCode =
    group.join_code ||
    group.code ||
    'Pending';


  $('groupFormArea').innerHTML = `

    <div class="group-created-success">

      <div class="big-success-tick">
        ✓
      </div>


      <h2>
        Selling Group Created
      </h2>


      <p>
        You are the owner of this group.
      </p>


      <div class="join-code-box">

        <small>
          Group Joining Code
        </small>


        <div class="join-code-value">

          <b id="createdJoinCode">
            ${esc(joinCode)}
          </b>


          <button
            class="secondary"
            onclick="copyGroupCode(
              '${esc(joinCode)}'
            )"
          >
            📋 Copy
          </button>

        </div>


        <p>
          Share this code only with farmers
          you want to invite.
        </p>

      </div>


      <button
        class="primary"
        onclick="openGroupSellingPage()"
      >
        View My Group
      </button>

    </div>

  `;

}

async function copyGroupCode(code) {

  try {

    await navigator
      .clipboard
      .writeText(code);


    toast(
      'Group code copied'
    );

  }

  catch {

    toast(
      `Group code: ${code}`
    );

  }

}

function showJoinGroupForm() {

  $('groupFormArea').innerHTML = `

    <div class="group-form-card join-group-card">


      <div class="group-form-title">

        <div>

          <h3>
            🔑 Join Selling Group
          </h3>

          <p>
            Enter the group code shared by the owner.
          </p>

        </div>

      </div>


      <div class="join-code-entry">


        <input
          id="joinGroupCode"
          class="control group-code-input"
          placeholder="Example: GT-CBE-4821"
          autocomplete="off"
        >


        <button
          class="primary"
          onclick="findSellingGroupByCode()"
        >
          Find Group
        </button>


      </div>


      <div id="joinGroupPreview"></div>


    </div>

  `;

}

async function findSellingGroupByCode() {

  try {

    const code =
      $('joinGroupCode')
        .value
        .trim()
        .toUpperCase();


    if (!code) {

      throw new Error(
        'Enter a joining code'
      );

    }


    const group =
      await api(

        `/api/v2/groups/by-code/${encodeURIComponent(code)}`

      );


    $('joinGroupPreview').innerHTML = `

      <div class="join-group-preview">


        <div class="group-preview-head">

          <div>

            <span class="verified-badge">
              ✓ GRAM Farmer Group
            </span>

            <h3>
              ${esc(group.name)}
            </h3>

            <p>
              ${esc(group.district)},
              ${esc(group.state || 'Tamil Nadu')}
            </p>

          </div>


          <span class="tag">
            ${esc(group.status || 'OPEN')}
          </span>

        </div>


        <div class="mini-grid">


          <span>

            Crop

            <b>
              ${esc(group.crop)}
            </b>

          </span>


          <span>

            Owner

            <b>
              ${esc(group.owner_name || 'Group Owner')}
            </b>

          </span>


          <span>

            Members

            <b>
              ${Number(group.member_count || 1)}
            </b>

          </span>


          <span>

            Group Quantity

            <b>
              ${num(group.current_quantity_qtl || 0)} qtl
            </b>

          </span>


          <span>

            Target

            <b>
              ${num(group.target_quantity_qtl || 0)} qtl
            </b>

          </span>


          <span>

            Shared Transport

            <b>
              ${group.shared_transport ? '✓ Yes' : 'No'}
            </b>

          </span>


        </div>


        <div class="field">

          <label>
            Quantity you want to add (qtl)
          </label>

          <input
            id="joinQuantity"
            class="control"
            type="number"
            value="5"
            min="1"
          >

        </div>


        <div class="field">

          <label>
            Message to Group Owner
          </label>

          <textarea
            id="joinMessage"
            class="control"
            rows="3"
            placeholder="I would like to join this group with my crop quantity."
          ></textarea>

        </div>


        <button
          class="primary wide"
          onclick="
            sendGroupJoinRequest(
              ${group.id},
              '${esc(code)}'
            )
          "
        >
          Send Join Request
        </button>


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}
async function sendGroupJoinRequest(
  groupId,
  code
) {

  try {

    const quantity =
      Number(
        $('joinQuantity').value
      );


    const message =
      $('joinMessage')
        .value
        .trim();


    if (!quantity || quantity <= 0) {

      throw new Error(
        'Enter valid quantity'
      );

    }


    await api(

      `/api/v2/groups/${groupId}/join-request`,

      {

        method: 'POST',

        body: JSON.stringify({

          join_code: code,

          quantity_qtl: quantity,

          message: message

        })

      }

    );


    $('joinGroupPreview').innerHTML = `

      <div class="join-request-success">

        <div class="request-icon">
          ✓
        </div>

        <h3>
          Request Sent
        </h3>

        <p>
          Your request has been sent to the
          group owner for approval.
        </p>

        <span class="pending-request-badge">
          Pending Owner Approval
        </span>

      </div>

    `;


    toast(
      'Join request sent to group owner'
    );


  }

  catch (e) {

    toast(e.message);

  }

}

async function loadMySellingGroups() {

  try {

    const groups =
      await api(
        '/api/v2/groups/my-groups'
      );


    if (!groups.length) {

      $('mySellingGroups').innerHTML = `

        <div class="empty group-empty">

          You have not created or joined
          any selling groups yet.

        </div>

      `;

      return;

    }


    $('mySellingGroups').innerHTML = `

      <div class="my-group-section">

        <h2>
          My Selling Groups
        </h2>


        <div class="selling-group-grid">


          ${groups.map(g => `

            <div class="selling-group-card">


              <div class="selling-group-card-head">

                <div>

                  ${
                    Number(g.owner_id) ===
                    Number(me.id)

                      ? `
                        <span class="owner-badge">
                          ★ Group Owner
                        </span>
                      `

                      : `
                        <span class="member-badge">
                          ✓ Member
                        </span>
                      `
                  }


                  <h3>
                    ${esc(g.name)}
                  </h3>

                  <p>
                    ${esc(g.crop)}
                    • ${esc(g.district)}
                  </p>

                </div>


                <span class="tag">
                  ${esc(g.status || 'OPEN')}
                </span>

              </div>


              <div class="mini-grid">

                <span>

                  Members

                  <b>
                    ${Number(g.member_count || 1)}
                  </b>

                </span>


                <span>

                  Quantity

                  <b>
                    ${num(g.current_quantity_qtl || 0)} qtl
                  </b>

                </span>


                <span>

                  Target

                  <b>
                    ${num(g.target_quantity_qtl || 0)} qtl
                  </b>

                </span>


                <span>

                  Join Code

                  <b class="mini-code">
                    ${esc(g.join_code || '—')}
                  </b>

                </span>

              </div>


              <div class="action-row">


                <button
                  class="secondary"
                  onclick="viewSellingGroup(${g.id})"
                >
                  View Group
                </button>


                ${
                  Number(g.owner_id) ===
                  Number(me.id)

                    ? `
                      <button
                        class="primary"
                        onclick="viewGroupJoinRequests(${g.id})"
                      >
                        Join Requests
                        ${
                          Number(g.pending_requests || 0)
                            ? `(${Number(g.pending_requests)})`
                            : ''
                        }
                      </button>
                    `

                    : ''
                }


              </div>


            </div>

          `).join('')}


        </div>

      </div>

    `;


  }

  catch (e) {

    console.error(e);

  }

}

async function viewGroupJoinRequests(groupId) {

  try {

    const requests =
      await api(
        `/api/v2/groups/${groupId}/join-requests`
      );


    $('groupFormArea').innerHTML = `

      <div class="group-form-card">


        <div class="group-form-title">

          <div>

            <h3>
              👤 Pending Join Requests
            </h3>

            <p>
              Review farmers before adding them
              to your selling group.
            </p>

          </div>

        </div>


        ${

          requests.length

            ? requests.map(r => `

                <div class="group-request-card">


                  <div class="request-farmer-info">


                    <div class="buyer-avatar">

                      ${esc(
                        String(
                          r.farmer_name || 'F'
                        )
                          .charAt(0)
                          .toUpperCase()
                      )}

                    </div>


                    <div>

                      <h3>
                        ${esc(r.farmer_name)}
                      </h3>

                      <p>
                        ${esc(
                          r.district ||
                          'Tamil Nadu'
                        )}
                      </p>

                    </div>


                  </div>


                  <div class="request-details">


                    <span>

                      Quantity

                      <b>
                        ${num(r.quantity_qtl)} qtl
                      </b>

                    </span>


                    <span>

                      Status

                      <b>
                        ${esc(r.status)}
                      </b>

                    </span>


                  </div>


                  <p class="request-message">

                    ${esc(
                      r.message ||
                      'No message provided.'
                    )}

                  </p>


                  ${
                    r.status === 'PENDING'

                      ? `

                        <div class="request-actions">

                          <button
                            class="danger-btn"
                            onclick="
                              respondGroupJoinRequest(
                                ${r.id},
                                'DECLINE',
                                ${groupId}
                              )
                            "
                          >
                            Decline
                          </button>


                          <button
                            class="primary"
                            onclick="
                              respondGroupJoinRequest(
                                ${r.id},
                                'ACCEPT',
                                ${groupId}
                              )
                            "
                          >
                            ✓ Accept Farmer
                          </button>

                        </div>

                      `

                      : `

                        <span class="tag">
                          ${esc(r.status)}
                        </span>

                      `
                  }


                </div>

              `).join('')

            : `

              <div class="empty">
                No pending join requests.
              </div>

            `

        }


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}

async function respondGroupJoinRequest(
  requestId,
  action,
  groupId
) {

  try {

    await api(

      `/api/v2/groups/join-requests/${requestId}`,

      {

        method: 'PATCH',

        body: JSON.stringify({

          action: action

        })

      }

    );


    toast(

      action === 'ACCEPT'
        ? 'Farmer accepted into group'
        : 'Join request declined'

    );


    await viewGroupJoinRequests(
      groupId
    );


    await loadMySellingGroups();


  }

  catch (e) {

    toast(e.message);

  }

}
async function viewSellingGroup(groupId) {

  try {

    const g =
      await api(
        `/api/v2/groups/${groupId}`
      );


    $('groupFormArea').innerHTML = `

      <div class="group-detail-card">


        <div class="group-detail-head">

          <div>

            ${
              Number(g.owner_id) === Number(me.id)

                ? `
                  <span class="owner-badge">
                    ★ You are Group Owner
                  </span>
                `

                : `
                  <span class="member-badge">
                    ✓ Group Member
                  </span>
                `
            }


            <h2>
              ${esc(g.name)}
            </h2>


            <p>
              ${esc(g.crop)}
              • ${esc(g.district)}
              • Tamil Nadu
            </p>

          </div>


          <span class="tag">
            ${esc(g.status || 'OPEN')}
          </span>

        </div>



        <div class="group-code-large">

          <small>
            Joining Code
          </small>

          <b>
            ${esc(g.join_code || '—')}
          </b>

          ${
            Number(g.owner_id) === Number(me.id)

              ? `

                <button
                  class="secondary"
                  onclick="
                    copyGroupCode(
                      '${esc(g.join_code || '')}'
                    )
                  "
                >
                  📋 Copy Code
                </button>

              `

              : ''
          }

        </div>



        <div class="mini-grid">

          <span>

            Owner

            <b>
              ${esc(g.owner_name)}
            </b>

          </span>


          <span>

            Members

            <b>
              ${Number(g.member_count || 1)}
            </b>

          </span>


          <span>

            Current Quantity

            <b>
              ${num(g.current_quantity_qtl || 0)} qtl
            </b>

          </span>


          <span>

            Target Quantity

            <b>
              ${num(g.target_quantity_qtl || 0)} qtl
            </b>

          </span>


          <span>

            Expected Price

            <b>
              ${fmt(g.expected_price || 0)}/qtl
            </b>

          </span>


          <span>

            Shared Transport

            <b>
              ${g.shared_transport ? '✓ Yes' : 'No'}
            </b>

          </span>


        </div>



        <h3 class="member-heading">
          Group Members
        </h3>


        <div class="group-member-list">

          ${(g.members || []).map(m => `

            <div class="group-member-row">


              <div class="buyer-avatar">

                ${esc(
                  String(
                    m.name || 'F'
                  )
                    .charAt(0)
                    .toUpperCase()
                )}

              </div>


              <div>

                <b>
                  ${esc(m.name)}
                </b>

                <small>
                  ${esc(m.district || 'Tamil Nadu')}
                </small>

              </div>


              <span>
                ${num(m.quantity_qtl || 0)} qtl
              </span>


              ${
                Number(m.user_id) === Number(g.owner_id)

                  ? `
                    <span class="owner-badge">
                      Owner
                    </span>
                  `

                  : ''
              }


            </div>

          `).join('')}

        </div>


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}

async function paymentsRewardsPage() {

  try {

    const [
      pay,
      rewardsData,
      catalog,
      redeemed,
      status
    ] = await Promise.all([
      api('/api/v2/payments'),
      api('/api/v2/rewards/me'),
      api('/api/v2/v3/reward-catalog'),
      api('/api/v2/v3/reward-redemptions'),
      api('/api/v2/v3/me-status')
    ]);


    // =========================================================
    // BUYER PAGE
    // Keep buyer rewards simple for now.
    // =========================================================

    if (me.role === 'buyer') {

      const cancelStreak = 6;

      $('content').innerHTML = `

        <div class="grid stats-4">

          ${card(
            tr('rewardPoints'),
            status.reward_points || 0,
            'Available to redeem',
            'green'
          )}

          ${card(
            tr('cashback'),
            fmt(rewardsData.benefit_rupees || 0),
            'Earned benefits'
          )}

          ${card(
            tr('cancellation'),
            `${cancelStreak} order streak`,
            'Reliable procurement'
          )}

          ${card(
            tr('securePayment'),
            'Signature + Webhook',
            'Secure buyer payments'
          )}

        </div>


        ${renderPaymentHistory(pay)}


        ${renderRewardCatalog(
          catalog,
          redeemed
        )}

      `;

      return;
    }



    // =========================================================
    // FARMER INNOVATION ENGINE
    // =========================================================


    const points =
      Number(status.reward_points || 0);


    const cashback =
      Number(
        rewardsData.benefit_rupees || 0
      );


    // ---------------------------------------------------------
    // DEMO IMPACT VALUES
    // These are derived for prototype UI.
    // Later we can calculate them from actual sales.
    // ---------------------------------------------------------

    const marketGain =
      Math.max(
        1180,
        Math.round(points * 5.4)
      );


    const timingGain =
      Math.max(
        920,
        Math.round(points * 4.1)
      );


    const logisticsSaving =
      Math.max(
        420,
        Math.round(points * 1.9)
      );


    const collectiveGain =
      Math.max(
        340,
        Math.round(points * 1.55)
      );


    const totalImpact =
      marketGain +
      timingGain +
      logisticsSaving +
      collectiveGain;


    const baselineIncome =
      Math.max(
        21800,
        totalImpact * 7.2
      );


    const actualIncome =
      baselineIncome +
      totalImpact;


    const improvementPercent =
      baselineIncome > 0
        ? (
            totalImpact /
            baselineIncome *
            100
          ).toFixed(1)
        : '0.0';


    const trustScore =
      Math.min(
        96,
        72 + Math.floor(points / 12)
      );


    const impactScore =
      Math.min(
        98,
        68 + Math.floor(totalImpact / 400)
      );


    const smartRewardPoints =
      Math.max(
        25,
        Math.round(
          totalImpact / 70
        )
      );


    const cancelStreak = 4;


    // =========================================================
    // FARMER PAGE
    // =========================================================

    $('content').innerHTML = `

      <div class="farmer-rewards-page">


        <!-- ===============================================
             HERO
        ================================================ -->

        <div class="fr-hero">

          <div class="fr-hero-content">

            <span class="fr-eyebrow">
              🌱 Farmer Financial Benefit Engine
            </span>

            <h2>
              GRAM AI Profit & Rewards
            </h2>

            <p>
              GRAM AI does not reward you only for using
              the platform. Rewards are linked with better
              selling decisions, verified transactions,
              logistics savings and farmer reliability.
            </p>

            <div class="fr-hero-tags">

              <span>
                🧠 AI Decision Rewards
              </span>

              <span>
                💰 Profit Improvement
              </span>

              <span>
                🚚 Logistics Savings
              </span>

              <span>
                🤝 Trust Benefits
              </span>

            </div>

          </div>


          <div class="fr-impact-highlight">

            <small>
              GRAM AI Value Added
            </small>

            <strong>
              ${fmt(totalImpact)}
            </strong>

            <span>
              estimated additional farmer value
            </span>

            <div class="fr-impact-growth">
              ↑ ${improvementPercent}% improvement
            </div>

          </div>

        </div>



        <!-- ===============================================
             TOP STATS
        ================================================ -->

        <div class="fr-stat-grid">


          <div class="fr-stat-card primary">

            <div class="fr-stat-icon">
              🌾
            </div>

            <div>

              <small>
                GramPoints
              </small>

              <strong>
                ${points}
              </strong>

              <span>
                Available for farmer benefits
              </span>

            </div>

          </div>



          <div class="fr-stat-card">

            <div class="fr-stat-icon">
              📈
            </div>

            <div>

              <small>
                GRAM AI Profit Added
              </small>

              <strong>
                ${fmt(totalImpact)}
              </strong>

              <span>
                This season
              </span>

            </div>

          </div>



          <div class="fr-stat-card">

            <div class="fr-stat-icon">
              🚚
            </div>

            <div>

              <small>
                Money Saved
              </small>

              <strong>
                ${fmt(
                  logisticsSaving +
                  cashback
                )}
              </strong>

              <span>
                Logistics + benefits
              </span>

            </div>

          </div>



          <div class="fr-stat-card">

            <div class="fr-stat-icon">
              🛡️
            </div>

            <div>

              <small>
                Farmer Trust Score
              </small>

              <strong>
                ${trustScore}/100
              </strong>

              <span>
                Reliable Seller
              </span>

            </div>

          </div>


        </div>



        <!-- ===============================================
             PROFIT IMPROVEMENT SCORE
        ================================================ -->

        <section class="fr-section">

          <div class="fr-section-head">

            <div>

              <span class="fr-section-icon">
                🧠
              </span>

              <div>

                <h3>
                  Profit Improvement Score
                </h3>

                <p>
                  Measures whether GRAM AI decisions
                  improved your actual farmer realization.
                </p>

              </div>

            </div>


            <span class="fr-score-badge">
              ${impactScore}/100 Impact Score
            </span>

          </div>



          <div class="fr-profit-grid">


            <div class="fr-profit-summary">

              <div class="fr-income-row">

                <span>
                  Estimated net without GRAM AI
                </span>

                <b>
                  ${fmt(baselineIncome)}
                </b>

              </div>


              <div class="fr-income-row">

                <span>
                  Actual / optimized realization
                </span>

                <b>
                  ${fmt(actualIncome)}
                </b>

              </div>


              <div class="fr-income-row gain">

                <span>
                  Farmer Gain
                </span>

                <b>
                  +${fmt(totalImpact)}
                </b>

              </div>


              <div class="fr-improvement-bar">

                <div
                  class="fr-improvement-fill"
                  style="
                    width:${Math.min(
                      100,
                      Number(improvementPercent) * 5
                    )}%
                  "
                ></div>

              </div>


              <div class="fr-improvement-caption">

                <b>
                  +${improvementPercent}%
                </b>

                <span>
                  estimated profit improvement
                </span>

              </div>

            </div>



            <div class="fr-profit-reasons">

              <h4>
                Why your realization improved
              </h4>


              <div class="fr-reason-item">

                <span>
                  🏪
                </span>

                <div>

                  <b>
                    Better Market Selection
                  </b>

                  <small>
                    +${fmt(marketGain)}
                  </small>

                </div>

              </div>


              <div class="fr-reason-item">

                <span>
                  ⏳
                </span>

                <div>

                  <b>
                    Better Selling Time
                  </b>

                  <small>
                    +${fmt(timingGain)}
                  </small>

                </div>

              </div>


              <div class="fr-reason-item">

                <span>
                  🚚
                </span>

                <div>

                  <b>
                    Logistics Optimization
                  </b>

                  <small>
                    ${fmt(logisticsSaving)} saved
                  </small>

                </div>

              </div>


              <div class="fr-reason-item">

                <span>
                  👥
                </span>

                <div>

                  <b>
                    Collective Selling Benefit
                  </b>

                  <small>
                    +${fmt(collectiveGain)}
                  </small>

                </div>

              </div>

            </div>


          </div>

        </section>



        <!-- ===============================================
             HOW GRAM AI HELPED YOU
        ================================================ -->

        <section class="fr-section">

          <div class="fr-section-head">

            <div>

              <span class="fr-section-icon">
                📍
              </span>

              <div>

                <h3>
                  How GRAM AI Helped You
                </h3>

                <p>
                  Every verified economic benefit becomes
                  part of your farmer impact history.
                </p>

              </div>

            </div>

            <span class="fr-verified-chip">
              ✓ Outcome Linked
            </span>

          </div>



          <div class="fr-impact-timeline">


            ${farmerImpactItem(
              '🧠',
              'WAIT recommendation followed',
              'Tomato price improved before sale',
              `+${fmt(timingGain)}`,
              '+40 GramPoints'
            )}


            ${farmerImpactItem(
              '🏪',
              'Better market selected',
              'Net Realizable Price was higher after transport costs',
              `+${fmt(marketGain)}`,
              '+35 GramPoints'
            )}


            ${farmerImpactItem(
              '🚚',
              'Shared transport used',
              'Transport cost reduced through route sharing',
              `${fmt(logisticsSaving)} saved`,
              '+25 GramPoints'
            )}


            ${farmerImpactItem(
              '👥',
              'Collective selling benefit',
              'Group sale improved farmer bargaining power',
              `+${fmt(collectiveGain)}`,
              '1.5× Reward Multiplier'
            )}


          </div>

        </section>



        <!-- ===============================================
             SMART REWARD ENGINE
        ================================================ -->

        <section class="fr-section">

          <div class="fr-section-head">

            <div>

              <span class="fr-section-icon">
                ✨
              </span>

              <div>

                <h3>
                  Smart Reward Engine
                </h3>

                <p>
                  GRAM AI rewards verified farmer outcomes,
                  not just clicks or app usage.
                </p>

              </div>

            </div>

            <span class="fr-ai-badge">
              AI Outcome Rewards
            </span>

          </div>



          <div class="fr-reward-rule-grid">


            ${farmerRewardRule(
              '🧠',
              'Smart Decision Reward',
              'Follow a successful SELL / WAIT / SHIFT MARKET recommendation.',
              '+20–60 points'
            )}


            ${farmerRewardRule(
              '🤝',
              'Fair Buyer Reward',
              'Complete a transaction with a reliable verified buyer.',
              '+25 points'
            )}


            ${farmerRewardRule(
              '🚚',
              'Shared Logistics Reward',
              'Reduce delivery cost through shared transportation.',
              '+25 points'
            )}


            ${farmerRewardRule(
              '🔍',
              'Quality Improvement Reward',
              'Improve verified produce grade across harvests.',
              '+40 points'
            )}


            ${farmerRewardRule(
              '📊',
              'Verified Data Contribution',
              'Provide verified selling outcome and market information.',
              '+15 points'
            )}


            ${farmerRewardRule(
              '👥',
              'Collective Selling Multiplier',
              'Complete successful FPO or group selling.',
              '1.5× points'
            )}


          </div>


          <div class="fr-next-reward">

            <div>

              <span>
                🤖
              </span>

              <div>

                <small>
                  AI Next Best Reward
                </small>

                <b>
                  Shared Logistics Cashback
                </b>

                <p>
                  Based on your activity, reducing your
                  next transport cost provides the
                  highest estimated farmer benefit.
                </p>

              </div>

            </div>


            <div class="fr-next-value">

              <small>
                Potential Reward
              </small>

              <strong>
                +${smartRewardPoints} pts
              </strong>

            </div>

          </div>

        </section>



        <!-- ===============================================
             FARMER TRUST / GRAM GUARANTEE
        ================================================ -->

        <section class="fr-section">

          <div class="fr-section-head">

            <div>

              <span class="fr-section-icon">
                🛡️
              </span>

              <div>

                <h3>
                  GramGuarantee Trust Benefits
                </h3>

                <p>
                  Reliable fulfilment unlocks better
                  financial and market-linkage benefits.
                </p>

              </div>

            </div>

            <span class="fr-trust-score">
              ${trustScore}/100
            </span>

          </div>



          <div class="fr-trust-grid">


            <div class="fr-trust-card">

              <span>
                ✅
              </span>

              <div>

                <b>
                  Reliable Fulfilment
                </b>

                <p>
                  ${cancelStreak} successful-order streak
                </p>

              </div>

            </div>



            <div class="fr-trust-card">

              <span>
                🎯
              </span>

              <div>

                <b>
                  Better Buyer Matching
                </b>

                <p>
                  High-trust farmers can receive
                  priority matching.
                </p>

              </div>

            </div>



            <div class="fr-trust-card">

              <span>
                🔐
              </span>

              <div>

                <b>
                  Lower Future Deposit Risk
                </b>

                <p>
                  Reliable transactions can support
                  lower trust requirements.
                </p>

              </div>

            </div>



            <div class="fr-trust-card">

              <span>
                ⭐
              </span>

              <div>

                <b>
                  Verified Farmer Reputation
                </b>

                <p>
                  Strong fulfilment history improves
                  marketplace credibility.
                </p>

              </div>

            </div>


          </div>

        </section>



        <!-- ===============================================
             PAYMENT HISTORY
        ================================================ -->

        ${renderPaymentHistory(pay)}



        <!-- ===============================================
             REWARD MARKETPLACE
        ================================================ -->

        <section class="fr-section">

          <div class="fr-section-head">

            <div>

              <span class="fr-section-icon">
                🎁
              </span>

              <div>

                <h3>
                  Farmer Benefit Marketplace
                </h3>

                <p>
                  Use GramPoints for benefits that can
                  directly reduce selling costs.
                </p>

              </div>

            </div>


            <span class="fr-points-balance">
              ${points} points available
            </span>

          </div>



          <div class="reward-grid">

            ${
              catalog.map(item => `

                <div class="reward-card">

                  <span>
                    🎁
                  </span>

                  <h3>
                    ${esc(item.title)}
                  </h3>

                  <p>
                    ${esc(item.description)}
                  </p>

                  <div>

                    <b>
                      ${Number(item.points_cost)} points
                    </b>

                    ${
                      item.benefit_rupees
                        ? `
                          •
                          ${fmt(
                            item.benefit_rupees
                          )}
                        `
                        : ''
                    }

                  </div>


                  <button
                    class="primary"
                    onclick="
                      redeemReward(
                        '${esc(item.code)}'
                      )
                    "
                  >
                    ${tr('redeem')}
                  </button>

                </div>

              `).join('')
            }

          </div>



          <h3 class="fr-redeemed-title">
            Redeemed Benefits
          </h3>


          ${
            redeemed.length

              ? redeemed.map(item => `

                  <div class="list-item">

                    <div>

                      <b>
                        ${esc(item.title)}
                      </b>

                      <small>
                        ${esc(item.description)}
                      </small>

                    </div>

                    <span class="tag">

                      ${esc(item.status)}
                      •

                      ${
                        item.expires_at
                          ? new Date(
                              item.expires_at
                            ).toLocaleDateString(
                              'en-IN'
                            )
                          : 'No expiry'
                      }

                    </span>

                  </div>

                `).join('')

              : `

                <div class="empty">
                  No redeemed rewards yet.
                </div>

              `
          }



          <div class="warning-panel">

            <b>
              🛡️ Cancellation Protection
            </b>

            <p>
              Repeated cancellations reduce trust,
              may reduce reward eligibility and can
              affect buyer matching. Reliable
              fulfilment unlocks better rewards and
              trust benefits.
            </p>

          </div>

        </section>


      </div>

    `;


  } catch (e) {

    console.error(
      'Payments & Rewards failed:',
      e
    );

    $('content').innerHTML = `

      <div class="card error">

        <h3>
          Could not load Payments & Rewards
        </h3>

        <p>
          ${esc(e.message)}
        </p>

      </div>

    `;

  }

}
function renderPaymentHistory(payments) {

  const rows =
    Array.isArray(payments)
      ? payments
      : [];


  return `

    <section class="fr-section">

      <div class="fr-section-head">

        <div>

          <span class="fr-section-icon">
            💳
          </span>

          <div>

            <h3>
              Secure Payment History
            </h3>

            <p>
              Track token payments, transactions
              and refunds securely.
            </p>

          </div>

        </div>


        <span class="fr-verified-chip">
          🔐 Protected
        </span>

      </div>


      ${
        rows.length

          ? `

            <div class="table-wrap">

              <table>

                <thead>

                  <tr>

                    <th>
                      ID
                    </th>

                    <th>
                      Purpose
                    </th>

                    <th>
                      Amount
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      Refund
                    </th>

                  </tr>

                </thead>


                <tbody>

                  ${
                    rows.map(payment => `

                      <tr>

                        <td>
                          #${Number(payment.id)}
                        </td>

                        <td>
                          ${esc(
                            payment.purpose ||
                            'Payment'
                          )}
                        </td>

                        <td>
                          ${fmt(
                            payment.expected_amount_rupees ||
                            0
                          )}
                        </td>

                        <td>

                          <span class="tag">
                            ${esc(
                              payment.status ||
                              'PENDING'
                            )}
                          </span>

                        </td>

                        <td>

                          ${
                            payment.refunds?.length

                              ? payment.refunds
                                  .map(refund => `

                                    ${fmt(
                                      Number(
                                        refund.amount_paise ||
                                        0
                                      ) / 100
                                    )}

                                    •

                                    ${esc(
                                      refund.status ||
                                      ''
                                    )}

                                  `)
                                  .join('<br>')

                              : '—'
                          }

                        </td>

                      </tr>

                    `).join('')
                  }

                </tbody>

              </table>

            </div>

          `

          : `

            <div class="fr-empty-state">

              <span>
                💳
              </span>

              <b>
                No payment activity yet
              </b>

              <p>
                Completed token, order and refund
                transactions will appear here.
              </p>

            </div>

          `
      }

    </section>

  `;

}



function renderRewardCatalog(
  catalog,
  redeemed
) {

  const rewards =
    Array.isArray(catalog)
      ? catalog
      : [];


  const history =
    Array.isArray(redeemed)
      ? redeemed
      : [];


  return `

    ${section(
      tr('rewards'),

      `

        <div class="reward-grid">

          ${
            rewards.map(item => `

              <div class="reward-card">

                <span>
                  🎁
                </span>

                <h3>
                  ${esc(item.title)}
                </h3>

                <p>
                  ${esc(item.description)}
                </p>

                <div>

                  <b>
                    ${Number(
                      item.points_cost ||
                      0
                    )} points
                  </b>

                  ${
                    item.benefit_rupees
                      ? `
                        •
                        ${fmt(
                          item.benefit_rupees
                        )}
                      `
                      : ''
                  }

                </div>

                <button
                  class="primary"
                  onclick="
                    redeemReward(
                      '${esc(item.code)}'
                    )
                  "
                >
                  ${tr('redeem')}
                </button>

              </div>

            `).join('')
          }

        </div>


        <h3>
          Redeemed
        </h3>


        ${
          history.length

            ? history.map(item => `

                <div class="list-item">

                  <div>

                    <b>
                      ${esc(item.title)}
                    </b>

                    <small>
                      ${esc(item.description)}
                    </small>

                  </div>

                  <span class="tag">

                    ${esc(item.status)}

                    ${
                      item.expires_at
                        ? `
                          •
                          ${new Date(
                            item.expires_at
                          ).toLocaleDateString(
                            'en-IN'
                          )}
                        `
                        : ''
                    }

                  </span>

                </div>

              `).join('')

            : `

              <div class="empty">
                No redeemed rewards yet.
              </div>

            `
        }

      `

    )}

  `;

}



function farmerImpactItem(
  icon,
  title,
  description,
  value,
  reward
) {

  return `

    <div class="fr-impact-item">

      <div class="fr-impact-icon">
        ${icon}
      </div>


      <div class="fr-impact-main">

        <b>
          ${esc(title)}
        </b>

        <p>
          ${esc(description)}
        </p>

      </div>


      <div class="fr-impact-value">

        <strong>
          ${esc(value)}
        </strong>

        <span>
          ${esc(reward)}
        </span>

      </div>

    </div>

  `;

}



function farmerRewardRule(
  icon,
  title,
  description,
  reward
) {

  return `

    <div class="fr-reward-rule">

      <div class="fr-rule-icon">
        ${icon}
      </div>


      <div>

        <b>
          ${esc(title)}
        </b>

        <p>
          ${esc(description)}
        </p>

        <span>
          ${esc(reward)}
        </span>

      </div>

    </div>

  `;

}

async function redeemReward(code){

  try{

    let d = await api(
      `/api/v2/v3/rewards/${code}/redeem`,
      {
        method:'POST'
      }
    );

    toast(
      `Reward active until ${
        new Date(
          d.expires_at
        ).toLocaleDateString()
      }`
    );

    paymentsRewardsPage();

  }catch(e){

    toast(e.message);

  }

}



async function redeemReward(code){try{let d=await api(`/api/v2/v3/rewards/${code}/redeem`,{method:'POST'});toast(`Reward active until ${new Date(d.expires_at).toLocaleDateString()}`);paymentsRewardsPage()}catch(e){toast(e.message)}}

async function profilePage(){let [p,s]=await Promise.all([api('/api/profile'),api('/api/v2/v3/me-status')]);$('content').innerHTML=`<div class="profile-header"><div><h2>${esc(p.name)} ${s.verified?'<span class="verified-badge">✓ GRAM AI Verified</span>':''}</h2><p>${esc(p.district)}, ${esc(p.state||'Tamil Nadu')} • ${esc(p.phone||'')}</p></div>${badge(s.verified)}</div><div class="grid two">${section(tr('profileDetails'),`<div class="form-grid"><div class="field"><label>Name</label><input id="pfName" class="control" value="${esc(p.name)}"></div><div class="field"><label>Phone</label><input id="pfPhone" class="control" value="${esc(p.phone||'')}"></div><div class="field"><label>District</label><input id="pfDistrict" class="control" value="${esc(p.district||'')}"></div><div class="field"><label>State</label><input class="control" value="Tamil Nadu" disabled></div><div class="field full"><label>Address</label><input id="pfAddress" class="control" value="${esc(p.address||'')}"></div>${me.role==='farmer'?`<div class="field"><label>Farm area (acres)</label><input id="pfFarm" type="number" class="control" value="${p.farm_size_acres||0}"></div>`:''}</div><button class="primary" onclick="saveFullProfile()">Save</button>`)}${section(tr('bankDetails'),`<div class="form-grid"><div class="field"><label>Account holder</label><input id="pfBankName" class="control" value="${esc(p.bank_account_name||'')}"></div><div class="field"><label>Account last 4</label><input id="pfBankLast" class="control" maxlength="4" value="${esc(p.bank_account_last4||'')}"></div><div class="field"><label>IFSC</label><input id="pfIfsc" class="control" value="${esc(p.bank_ifsc||'')}"></div><div class="field"><label>UPI ID</label><input id="pfUpi" class="control" value="${esc(p.upi_id||'')}"></div></div><div class="security-note">Full bank account numbers and UPI PINs are never requested in this prototype.</div>`)}</div>${section(tr('kyc'),`<div class="kyc-status">${badge(s.verified)}<p>Method: ${esc(s.kyc.method||'Not started')} • ${esc(s.kyc.masked_document||'')}</p><p>Marketplace gate: ${s.verified?'Selling / ordering and payouts enabled.':'Selling / ordering and payouts blocked until verified.'}</p></div><div class="form-grid"><div class="field"><label>KYC method</label><select id="kycMethod" class="control"><option>AADHAAR</option><option>KYC</option></select></div><div class="field"><label>Aadhaar last 4 only</label><input id="kycLast" class="control" maxlength="4"></div><div class="field full"><label>Live selfie</label><input id="kycSelfie" class="control" type="file" accept="image/*" capture="user"></div></div><label><input id="kycConsent" type="checkbox"> I consent to secure verification.</label><button class="primary" onclick="submitLiveKyc()">Submit KYC + Live Photo</button><div class="warn-box">Demo accounts are pre-verified so the SIH workflow can be demonstrated. Newly registered accounts remain blocked until Admin verifies KYC. No full Aadhaar number is stored.</div>`)}`}
async function saveFullProfile(){try{let p=await api('/api/profile');await api('/api/profile',{method:'PATCH',body:JSON.stringify({...p,name:$('pfName').value,phone:$('pfPhone').value,district:$('pfDistrict').value,state:'Tamil Nadu',address:$('pfAddress').value,farm_size_acres:$('pfFarm')?+$('pfFarm').value:p.farm_size_acres,bank_account_name:$('pfBankName').value,bank_account_last4:$('pfBankLast').value,bank_ifsc:$('pfIfsc').value,upi_id:$('pfUpi').value})});toast('Profile updated')}catch(e){toast(e.message)}}
async function submitLiveKyc(){try{let f=$('kycSelfie').files[0];if(!f)throw Error('Take a live selfie');let fd=new FormData();fd.append('method',$('kycMethod').value);fd.append('aadhaar_last4',$('kycLast').value);fd.append('consent',$('kycConsent').checked?'true':'false');fd.append('selfie',f);let d=await api('/api/v2/v3/kyc-live',{method:'POST',body:fd});toast('KYC submitted to admin: '+d.status);profilePage()}catch(e){toast(e.message)}}

async function farmerFeedbackPage() {

  let orders = [];
  let feedbackHistory = [];

  // =========================================================
  // LOAD ORDERS
  // =========================================================

  try {

    orders = await api('/api/orders');

  } catch (e) {

    console.warn(
      'Could not load orders for feedback:',
      e
    );

  }


  // =========================================================
  // LOAD THIS USER'S PREVIOUS FEEDBACK
  // =========================================================

  try {

    feedbackHistory =
      await api('/api/v2/feedback');

    if (!Array.isArray(feedbackHistory)) {
      feedbackHistory = [];
    }

  } catch (e) {

    console.warn(
      'Could not load previous feedback:',
      e
    );

    feedbackHistory = [];

  }
  const orderHtml = orders.length
    ? orders.map(o => `
        <div class="farmer-feedback-order">
          <div class="ff-order-main">
            <div class="ff-order-icon">📦</div>

            <div>
              <b>Order #${o.id} • ${esc(o.crop || 'Crop')}</b>

              <small>
                ${esc(o.status || '—')}
                •
                ${fmt(o.total || 0)}
              </small>
            </div>
          </div>

          <button
            class="secondary"
            onclick="openOrderFeedback(${o.id})"
          >
            ⭐ Rate Order
          </button>
        </div>
      `).join('')
    : `
        <div class="ff-empty">
          <div class="ff-empty-icon">🌾</div>
          <b>No orders available for rating yet</b>
          <p>
            After completing an order, you can rate the buyer,
            transport experience and transaction here.
          </p>
        </div>
      `;
  // =========================================================
  // PREVIOUS FEEDBACK HISTORY
  // =========================================================

  const feedbackHistoryHtml =
    feedbackHistory.length

      ? feedbackHistory.map(f => {

          const status =
            f.review_status ||
            f.status ||
            'SUBMITTED';

          const date =
            f.created_at
              ? new Date(
                  f.created_at
                ).toLocaleString(
                  'en-IN'
                )
              : '—';


          // Old versions stored structured information
          // inside the message. Hide that technical JSON
          // from the farmer.

          let cleanMessage =
            String(
              f.message || ''
            );

          if (
            cleanMessage.includes(
              '--- GRAM AI FARMER VOICE DATA ---'
            )
          ) {

            cleanMessage =
              cleanMessage
                .split(
                  '--- GRAM AI FARMER VOICE DATA ---'
                )[0]
                .trim();

          }


          const ratings = [

            Number(
              f.price_forecast_rating || 0
            ),

            Number(
              f.buyer_experience_rating || 0
            ),

            Number(
              f.payment_rating || 0
            ),

            Number(
              f.transport_rating || 0
            ),

            Number(
              f.quality_grade_rating || 0
            ),

            Number(
              f.ease_of_use_rating || 0
            )

          ].filter(x => x > 0);


          const avgRating =
            ratings.length

              ? (
                  ratings.reduce(
                    (a, b) => a + b,
                    0
                  )
                  / ratings.length
                ).toFixed(1)

              : Number(
                  f.rating || 0
                ).toFixed(1);


          const requirements =
            Array.isArray(
              f.local_requirements
            )
              ? f.local_requirements
              : [];


          const votes =
            Array.isArray(
              f.feature_votes
            )
              ? f.feature_votes
              : [];


          const statusClass =
            String(status)
              .toUpperCase()
              .replace(
                /[^A-Z0-9_-]/g,
                '-'
              );


          return `

            <div class="farmer-feedback-order">

              <div class="ff-order-main">

                <div class="ff-order-icon">
                  💬
                </div>

                <div>

                  <b>
                    Feedback #${Number(f.id)}
                  </b>

                  <small>
                    ${esc(date)}
                  </small>

                  ${
                    cleanMessage

                      ? `
                          <p style="
                            margin:6px 0 0;
                            color:#4b6354;
                          ">
                            ${esc(cleanMessage)}
                          </p>
                        `

                      : `
                          <p style="
                            margin:6px 0 0;
                            color:#718075;
                          ">
                            Farmer feedback submitted
                          </p>
                        `
                  }


                  <div
                    style="
                      display:flex;
                      flex-wrap:wrap;
                      gap:6px;
                      margin-top:8px;
                    "
                  >

                    ${
                      Number(avgRating) > 0

                        ? `
                            <span class="tag">
                              ⭐ ${avgRating}/5
                            </span>
                          `

                        : ''
                    }


                    ${
                      f.recommendation_followed

                        ? `
                            <span class="tag">
                              🧠 ${esc(
                                f.recommendation_followed
                              )}
                            </span>
                          `

                        : ''
                    }


                    ${
                      requirements.length

                        ? `
                            <span class="tag">
                              🏘 ${requirements.length}
                              local requirement${
                                requirements.length === 1
                                  ? ''
                                  : 's'
                              }
                            </span>
                          `

                        : ''
                    }


                    ${
                      votes.length

                        ? `
                            <span class="tag">
                              🗳 Feature voted
                            </span>
                          `

                        : ''
                    }

                  </div>

                </div>

              </div>


              <div>

                <span
                  class="tag ${statusClass.toLowerCase()}"
                >
                  ${esc(status)}
                </span>

              </div>

            </div>

          `;

        }).join('')

      : `

          <div class="ff-empty">

            <div class="ff-empty-icon">
              💬
            </div>

            <b>
              No feedback submitted yet
            </b>

            <p>
              Your submitted feedback,
              requirements and feature votes
              will appear here.
            </p>

          </div>

        `;

  $('content').innerHTML = `

    <div class="farmer-feedback-page">

      <!-- ==========================
           PAGE HEADER
      =========================== -->

      <div class="ff-hero">

        <div class="ff-hero-copy">

          <span class="ff-eyebrow">
            🌱 Farmer Voice
          </span>
          <span style="
  display:inline-flex;
  align-items:center;
  margin-left:8px;
  padding:5px 10px;
  border-radius:20px;
  background:#fff3cd;
  color:#795500;
  font-size:12px;
  font-weight:700;
  border:1px solid #ffe69c;
">
  ✨ NEW FEEDBACK MODE
</span>

          <h2>
            Help Build GRAM AI With Us
          </h2>

          <p>
            Your feedback does more than improve the app.
            It can improve our price forecasts, buyer matching,
            logistics recommendations and services for farmers
            in your area.
          </p>

          <div class="ff-hero-tags">
            <span>🎙 Voice Enabled</span>
            <span>🔐 Privacy Controls</span>
            <span>🧠 AI Assisted</span>
            <span>🎁 GramPoints Eligible</span>
          </div>

        </div>

        <div class="ff-impact-card">

          <span class="ff-impact-icon">
            🤝
          </span>

          <b>
            Farmer Co-Design
          </b>

          <p>
            Suggest what GRAM AI should build next and track
            whether your idea is reviewed or implemented.
          </p>

        </div>

      </div>


      <!-- ==========================
           QUICK EXPERIENCE
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>
            <span class="ff-section-icon">⚡</span>

            <div>
              <h3>
                Quick Experience Check
              </h3>

              <p>
                Tell us which part of GRAM AI helped you
                and where we need to improve.
              </p>
            </div>
          </div>

        </div>


        <div class="ff-rating-grid">

          ${farmerFeedbackRatingCard(
            'forecast',
            '📈',
            'Price Forecast',
            'Was the predicted price useful?'
          )}

          ${farmerFeedbackRatingCard(
            'buyer',
            '🤝',
            'Buyer Experience',
            'Buyer reliability and negotiation'
          )}

          ${farmerFeedbackRatingCard(
            'payment',
            '💳',
            'Payment',
            'Payment speed and transparency'
          )}

          ${farmerFeedbackRatingCard(
            'transport',
            '🚚',
            'Transport',
            'Cost, availability and delivery'
          )}

          ${farmerFeedbackRatingCard(
            'quality',
            '🔍',
            'AI Quality Grade',
            'Was our crop grade accurate?'
          )}

          ${farmerFeedbackRatingCard(
            'usability',
            '📱',
            'Ease of Use',
            'Was GRAM AI simple to use?'
          )}

        </div>

      </div>


      <!-- ==========================
           RECOMMENDATION OUTCOME
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              🧠
            </span>

            <div>
              <h3>
                Did GRAM AI's Recommendation Help?
              </h3>

              <p>
                This helps us improve SELL, WAIT and
                SHIFT MARKET recommendations.
              </p>
            </div>

          </div>

          <span class="ff-innovation-badge">
            Model Learning Feedback
          </span>

        </div>


        <div class="ff-form-grid">

          <div class="field">

            <label>
              Recommendation you followed
            </label>

            <select
              id="ffRecommendation"
              class="control"
            >

              <option value="">
                Select recommendation
              </option>

              <option value="SELL_NOW">
                SELL NOW
              </option>

              <option value="WAIT">
                WAIT
              </option>

              <option value="SHIFT_MARKET">
                SHIFT MARKET
              </option>

              <option value="DID_NOT_FOLLOW">
                I did not follow it
              </option>

            </select>

          </div>


          <div class="field">

            <label>
              Was the recommendation useful?
            </label>

            <select
              id="ffRecommendationUseful"
              class="control"
            >

              <option value="">
                Select
              </option>

              <option value="VERY_USEFUL">
                Very Useful
              </option>

              <option value="USEFUL">
                Useful
              </option>

              <option value="PARTLY">
                Partly Useful
              </option>

              <option value="NOT_USEFUL">
                Not Useful
              </option>

            </select>

          </div>


          <div class="field">

            <label>
              GRAM AI expected price / qtl
            </label>

            <input
              id="ffExpectedPrice"
              class="control"
              type="number"
              min="0"
              placeholder="₹ Expected price"
            >

          </div>


          <div class="field">

            <label>
              Actual selling price / qtl
            </label>

            <input
              id="ffActualPrice"
              class="control"
              type="number"
              min="0"
              placeholder="₹ Actual selling price"
              oninput="updateFeedbackProfitImpact()"
            >

          </div>


          <div class="field">

            <label>
              Previous / alternative price / qtl
            </label>

            <input
              id="ffAlternativePrice"
              class="control"
              type="number"
              min="0"
              placeholder="₹ Other available price"
              oninput="updateFeedbackProfitImpact()"
            >

          </div>


          <div class="field">

            <label>
              Your outcome
            </label>

            <div
              id="ffProfitImpact"
              class="ff-profit-impact"
            >
              Add actual and alternative price to calculate impact.
            </div>

          </div>

        </div>

      </div>


      <!-- ==========================
           MARKET REALITY REPORT
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              📍
            </span>

            <div>
              <h3>
                Report Market Reality
              </h3>

              <p>
                Tell GRAM AI when the real market differs
                from our data.
              </p>
            </div>

          </div>

          <span class="ff-innovation-badge">
            Ground-Truth Data
          </span>

        </div>


        <div class="ff-form-grid">

          <div class="field">

            <label>
              What is different?
            </label>

            <select
              id="ffMarketIssue"
              class="control"
            >

              <option value="">
                Select
              </option>

              <option value="MANDI_PRICE">
                Mandi price is different
              </option>

              <option value="BUYER_QUOTE">
                Buyer quote is different
              </option>

              <option value="TRANSPORT_COST">
                Transport cost is different
              </option>

              <option value="MARKET_CHARGE">
                Commission / market charge is different
              </option>

              <option value="DEMAND">
                Actual demand is different
              </option>

              <option value="OTHER">
                Other
              </option>

            </select>

          </div>


          <div class="field">

            <label>
              Market / Buyer name
            </label>

            <input
              id="ffMarketName"
              class="control"
              placeholder="e.g. Coimbatore APMC / Buyer name"
            >

          </div>


          <div class="field">

            <label>
              Real price / cost
            </label>

            <input
              id="ffMarketValue"
              type="number"
              min="0"
              class="control"
              placeholder="₹ Enter observed value"
            >

          </div>


          <div class="field">

            <label>
              District
            </label>

            <input
              id="ffMarketDistrict"
              class="control"
              value="${esc(me?.district || '')}"
              placeholder="District"
            >

          </div>

        </div>


        <div class="ff-ground-note">

          <span>
            🛰
          </span>

          <div>
            <b>
              Why this matters
            </b>

            <p>
              Verified farmer reports can help GRAM AI detect
              outdated market information and improve future
              recommendations.
            </p>
          </div>

        </div>

      </div>


      <!-- ==========================
           LOCAL REQUIREMENTS
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              🏘
            </span>

            <div>

              <h3>
                What Does Your Area Need?
              </h3>

              <p>
                Request services that would improve selling
                opportunities for farmers in your area.
              </p>

            </div>

          </div>

        </div>


        <div class="ff-requirement-grid">

          ${farmerRequirementOption(
            'BUYER',
            '🤝',
            'More Verified Buyers'
          )}

          ${farmerRequirementOption(
            'TRANSPORT',
            '🚚',
            'Transport Availability'
          )}

          ${farmerRequirementOption(
            'COLD_STORAGE',
            '❄️',
            'Cold Storage'
          )}

          ${farmerRequirementOption(
            'COLLECTION_CENTER',
            '🏬',
            'Collection Centre'
          )}

          ${farmerRequirementOption(
            'FPO',
            '👥',
            'FPO / Group Selling'
          )}

          ${farmerRequirementOption(
            'PROCESSING',
            '🏭',
            'Processing Unit'
          )}

          ${farmerRequirementOption(
            'EXPORT',
            '🌍',
            'Export Buyer Access'
          )}

          ${farmerRequirementOption(
            'PACKAGING',
            '📦',
            'Packaging Support'
          )}

        </div>


        <div class="ff-form-grid ff-margin-top">

          <div class="field">

            <label>
              Crop affected
            </label>

            <input
              id="ffRequirementCrop"
              class="control"
              placeholder="e.g. Tomato"
            >

          </div>


          <div class="field">

            <label>
              Village / Area
            </label>

            <input
              id="ffRequirementArea"
              class="control"
              placeholder="Village / taluka / district"
            >

          </div>

        </div>

      </div>


      <!-- ==========================
           BUILD NEXT
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              🗳
            </span>

            <div>

              <h3>
                Vote: What Should GRAM AI Improve Next?
              </h3>

              <p>
                Vote for the next advanced capability you want GRAM AI to improve or add to the platform.
              </p>

            </div>

          </div>

          <span class="ff-innovation-badge">
            Farmer Co-Design
          </span>

        </div>


        <div class="ff-vote-grid">

        ${feedbackVoteCard(
  'storage_profit_optimizer',
  '❄️',
  'AI Storage Profit Optimizer',
  'Compare sell-now income with storage cost, spoilage risk and expected future profit.'
)}

${feedbackVoteCard(
  'auto_collective_matcher',
  '👥',
  'Auto Farmer Collective Matcher',
  'Automatically find nearby farmers with the same crop and harvest window for group selling.'
)}

${feedbackVoteCard(
  'demand_heatmap',
  '🔥',
  'Live Buyer Demand Heatmap',
  'Show verified crop demand intensity by district, quantity and required date.'
)}

${feedbackVoteCard(
  'ai_logistics_optimizer',
  '🚛',
  'AI Shared Logistics Optimizer',
  'Automatically combine compatible loads and routes to reduce transport cost per quintal.'
)}


          

        </div>

      </div>


      <!-- ==========================
           DETAILED FEEDBACK
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              💬
            </span>

            <div>

              <h3>
                Tell Us In Your Own Words
              </h3>

              <p>
                Share an idea, problem, requirement or experience.
              </p>

            </div>

          </div>

        </div>


        <div class="ff-feedback-box">

          <div class="field">

            <label>
              Feedback type
            </label>

            <select
              id="feedbackCat"
              class="control"
            >

              <option value="FEEDBACK">
                General Feedback
              </option>

              <option value="REQUIREMENT">
                New Requirement
              </option>

              <option value="FORECAST">
                Price Forecast
              </option>

              <option value="MARKET_DATA">
                Market Data
              </option>

              <option value="BUYER">
                Buyer Experience
              </option>

              <option value="PAYMENT">
                Payment
              </option>

              <option value="TRANSPORT">
                Transport
              </option>

              <option value="QUALITY_AI">
                AI Quality Grading
              </option>

              <option value="LANGUAGE">
                Language / Voice
              </option>

              <option value="APP_ISSUE">
                App Issue
              </option>

            </select>

          </div>


          <div class="field">

            <label>
              Overall GRAM AI rating
            </label>

            <select
              id="feedbackRating"
              class="control"
            >

              <option value="5">
                ⭐⭐⭐⭐⭐ Excellent
              </option>

              <option value="4">
                ⭐⭐⭐⭐ Good
              </option>

              <option value="3">
                ⭐⭐⭐ Average
              </option>

              <option value="2">
                ⭐⭐ Needs Improvement
              </option>

              <option value="1">
                ⭐ Poor
              </option>

            </select>

          </div>


          <div class="field full">

            <label>
              Your feedback / idea
            </label>

            <div class="ff-voice-input">

              <textarea
                id="feedbackMsg"
                class="control"
                rows="5"
                placeholder="Tell GRAM AI what happened, what should improve, or what farmers in your area need..."
              ></textarea>

              <button
                class="mic ff-mic"
                onclick="voiceInto('feedbackMsg')"
                title="Speak feedback"
              >
                🎙
              </button>

            </div>

          </div>


          <div class="ff-options-row">

            <label class="ff-check">

              <input
                id="ffAnonymous"
                type="checkbox"
              >

              <span>
                🕶 Submit anonymously to analytics
              </span>

            </label>


            <label class="ff-check">

              <input
                id="ffCallback"
                type="checkbox"
              >

              <span>
                📞 Request support callback
              </span>

            </label>


            <label class="ff-check">

              <input
                id="ffCommunity"
                type="checkbox"
                checked
              >

              <span>
                👥 Count this toward community demand
              </span>

            </label>

          </div>


          <div class="ff-submit-row">

            <div>

              <b>
                🎁 Useful verified feedback may earn GramPoints
              </b>

              <small>
                Market-data corrections are reviewed before
                being used by GRAM AI.
              </small>

            </div>

            <button
              class="primary ff-submit-btn"
              onclick="sendAdvancedFarmerFeedback()"
            >
              Submit New Feedback →
            </button>

          </div>

        </div>

      </div>


      <!-- ==========================
           ORDER FEEDBACK
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              ⭐
            </span>

            <div>
              <h3>
                Rate Your Completed Transactions
              </h3>

              <p>
                Buyer and transporter ratings improve trust
                for other farmers.
              </p>
            </div>

          </div>

        </div>

        <div class="ff-order-list">
          ${orderHtml}
        </div>

      </div>


      <!-- ==========================
           TRACK SUBMISSIONS
      =========================== -->

      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              📌
            </span>

            <div>

              <h3>
                My Feedback Journey
              </h3>

              <p>
                Track what happens after you submit an idea
                or requirement.
              </p>

            </div>

          </div>

        </div>


        <div class="ff-status-flow">

          <div class="ff-status-step active">
            <span>1</span>
            <b>Submitted</b>
          </div>

          <div class="ff-status-line"></div>

          <div class="ff-status-step">
            <span>2</span>
            <b>Reviewed</b>
          </div>

          <div class="ff-status-line"></div>

          <div class="ff-status-step">
            <span>3</span>
            <b>Planned</b>
          </div>

          <div class="ff-status-line"></div>

          <div class="ff-status-step">
            <span>4</span>
            <b>Implemented</b>
          </div>

        </div>


        <div class="info-panel">

          <b>
            💡 Closed-loop farmer feedback
          </b>

          <p>
            When an administrator reviews or implements your
            suggestion, GRAM AI can notify you instead of
            allowing feedback to disappear into a simple
            suggestion box.
          </p>

        </div>
                <div style="margin-top:22px;">

          <div
            style="
              display:flex;
              align-items:center;
              justify-content:space-between;
              gap:12px;
              margin-bottom:12px;
            "
          >

            <div>

              <h3 style="margin:0;">
                My Previous Feedback
              </h3>

              <p style="margin:4px 0 0;">
                Every submission is stored separately
                and receives its own feedback ID.
              </p>

            </div>

            <span class="ff-innovation-badge">
              ${feedbackHistory.length}
              Submission${
                feedbackHistory.length === 1
                  ? ''
                  : 's'
              }
            </span>

          </div>

          <div class="ff-order-list">

            ${feedbackHistoryHtml}

          </div>

        </div>

      </div>

    </div>
  `;
}

function farmerFeedbackRatingCard(
  key,
  icon,
  title,
  subtitle
) {
  return `
    <div class="ff-rating-card">

      <span class="ff-rating-icon">
        ${icon}
      </span>

      <div>
        <b>${esc(title)}</b>
        <small>${esc(subtitle)}</small>
      </div>

      <div
        class="ff-stars"
        data-feedback-key="${esc(key)}"
      >

        ${[1,2,3,4,5].map(n => `
          <button
            type="button"
            class="ff-star"
            data-value="${n}"
            onclick="
              setFarmerFeedbackRating(
                '${esc(key)}',
                ${n}
              )
            "
          >
            ★
          </button>
        `).join('')}

      </div>

      <input
        type="hidden"
        id="ffRating_${esc(key)}"
        value="0"
      >

    </div>
  `;
}


function setFarmerFeedbackRating(
  key,
  value
) {

  const input =
    $(`ffRating_${key}`);

  if (input) {
    input.value = value;
  }


  document
    .querySelectorAll(
      `[data-feedback-key="${key}"] .ff-star`
    )
    .forEach((star, index) => {

      star.classList.toggle(
        'selected',
        index < value
      );

    });

}


function farmerRequirementOption(
  value,
  icon,
  label
) {

  return `
    <label class="ff-requirement-card">

      <input
        type="checkbox"
        name="ffLocalRequirement"
        value="${esc(value)}"
      >

      <span class="ff-requirement-icon">
        ${icon}
      </span>

      <b>
        ${esc(label)}
      </b>

      <span class="ff-select-check">
        ✓
      </span>

    </label>
  `;
}


function feedbackVoteCard(
  value,
  icon,
  title,
  description
) {

  return `
    <label class="ff-vote-card">

      <input
        type="radio"
        name="ffFeatureVote"
        value="${esc(value)}"
      >

      <span class="ff-vote-icon">
        ${icon}
      </span>

      <div>
        <b>
          ${esc(title)}
        </b>

        <p>
          ${esc(description)}
        </p>
      </div>

      <span class="ff-vote-check">
        ✓
      </span>

    </label>
  `;
}


function updateFeedbackProfitImpact() {

  const actual =
    Number(
      $('ffActualPrice')?.value || 0
    );

  const alternative =
    Number(
      $('ffAlternativePrice')?.value || 0
    );

  const box =
    $('ffProfitImpact');


  if (!box) {
    return;
  }


  if (!actual || !alternative) {

    box.className =
      'ff-profit-impact';

    box.innerHTML =
      'Add actual and alternative price to calculate impact.';

    return;
  }


  const difference =
    actual - alternative;


  if (difference > 0) {

    box.className =
      'ff-profit-impact positive';

    box.innerHTML = `
      <b>+${fmt(difference)}/qtl</b>
      better than the alternative price
    `;

  }

  else if (difference < 0) {

    box.className =
      'ff-profit-impact negative';

    box.innerHTML = `
      <b>${fmt(Math.abs(difference))}/qtl</b>
      lower than the alternative price
    `;

  }

  else {

    box.className =
      'ff-profit-impact neutral';

    box.innerHTML =
      'Same as the alternative price.';

  }

}
let farmerFeedbackSubmitting = false;
async function sendAdvancedFarmerFeedback() {

  if (farmerFeedbackSubmitting) {
    return;
  }

  farmerFeedbackSubmitting = true;

  try {

    const submitBtn =
      document.querySelector('.ff-submit-btn');

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '⏳ Submitting...';
    }

    const message =
      $('feedbackMsg')?.value?.trim() || '';

    const category =
      $('feedbackCat')?.value || 'FEEDBACK';

    const rating =
      Number($('feedbackRating')?.value || 5);

    const requirements =
      Array.from(
        document.querySelectorAll(
          'input[name="ffLocalRequirement"]:checked'
        )
      ).map(x => x.value);

    const featureVote =
      document.querySelector(
        'input[name="ffFeatureVote"]:checked'
      )?.value || '';

    const priceForecastRating =
      Number($('ffRating_forecast')?.value || 0);

    const buyerExperienceRating =
      Number($('ffRating_buyer')?.value || 0);

    const paymentRating =
      Number($('ffRating_payment')?.value || 0);

    const transportRating =
      Number($('ffRating_transport')?.value || 0);

    const qualityRating =
      Number($('ffRating_quality')?.value || 0);

    const usabilityRating =
      Number($('ffRating_usability')?.value || 0);

    const recommendation =
      $('ffRecommendation')?.value || '';

    const recommendationUseful =
      $('ffRecommendationUseful')?.value || '';

    const expectedPrice =
      Number($('ffExpectedPrice')?.value || 0);

    const actualPrice =
      Number($('ffActualPrice')?.value || 0);

    const alternativePrice =
      Number($('ffAlternativePrice')?.value || 0);

    let outcome = '';

    if (actualPrice > 0 && alternativePrice > 0) {

      const diff =
        actualPrice - alternativePrice;

      if (diff > 0) {
        outcome = `BETTER_BY_${diff.toFixed(2)}`;
      } else if (diff < 0) {
        outcome =
          `LOWER_BY_${Math.abs(diff).toFixed(2)}`;
      } else {
        outcome = 'SAME_AS_ALTERNATIVE';
      }

    }

    const marketIssue =
      $('ffMarketIssue')?.value || '';

    const marketName =
      $('ffMarketName')?.value?.trim() || '';

    const marketValue =
      Number($('ffMarketValue')?.value || 0);

    const marketDistrict =
      $('ffMarketDistrict')?.value?.trim() || '';

    const requirementCrop =
      $('ffRequirementCrop')?.value?.trim() || '';

    const requirementArea =
      $('ffRequirementArea')?.value?.trim() || '';

    const anonymous =
      Boolean($('ffAnonymous')?.checked);

    const callbackRequested =
      Boolean($('ffCallback')?.checked);

    const extra = [];

    if (marketIssue) {
      extra.push(`Market reality: ${marketIssue}`);
    }

    if (marketName) {
      extra.push(`Market / Buyer: ${marketName}`);
    }

    if (marketValue > 0) {
      extra.push(`Observed value: ₹${marketValue}`);
    }

    if (marketDistrict) {
      extra.push(`District: ${marketDistrict}`);
    }

    if (requirementCrop) {
      extra.push(`Requirement crop: ${requirementCrop}`);
    }

    if (requirementArea) {
      extra.push(`Requirement area: ${requirementArea}`);
    }

    let finalMessage = message;

    if (extra.length) {
      finalMessage = [
        message,
        '',
        ...extra
      ].filter(Boolean).join('\n');
    }

    const hasAnyInput =
      Boolean(
        message ||
        requirements.length ||
        featureVote ||
        recommendation ||
        marketIssue ||
        marketName ||
        marketValue ||
        requirementCrop ||
        requirementArea ||
        priceForecastRating ||
        buyerExperienceRating ||
        paymentRating ||
        transportRating ||
        qualityRating ||
        usabilityRating
      );

    if (!hasAnyInput) {

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Submit Feedback →';
      }

      throw new Error(
        'Please enter feedback, rating, requirement, market report or feature vote.'
      );
    }

    const result = await api(
      '/api/v2/feedback',
      {
        method: 'POST',
        body: JSON.stringify({

          category,
          rating,

          message:
            finalMessage ||
            'Farmer feedback submitted through GRAM AI',

          voice_transcript: '',

          price_forecast_rating:
            priceForecastRating,

          buyer_experience_rating:
            buyerExperienceRating,

          payment_rating:
            paymentRating,

          transport_rating:
            transportRating,

          quality_grade_rating:
            qualityRating,

          ease_of_use_rating:
            usabilityRating,

          recommendation_followed:
            recommendation,

          recommendation_useful:
            recommendationUseful,

          expected_price:
            expectedPrice,

          actual_selling_price:
            actualPrice,

          alternative_price:
            alternativePrice,

          outcome,

          local_requirements:
            requirements,

          feature_votes:
            featureVote
              ? [featureVote]
              : [],

          anonymous,

          callback_requested:
            callbackRequested

        })
      }
    );

    const feedbackId =
      result.feedback_id ||
      result.id;

    toast(
      `✅ Feedback #${feedbackId} submitted successfully`
    );

    // Important:
    // Reload page after POST.
    // This resets the form and prevents update-like behavior.
    await farmerFeedbackPage();

    // Show confirmation after reload.
    $('modalBody').innerHTML = `
      <div style="text-align:center;padding:24px;">

        <div style="
          font-size:52px;
          margin-bottom:12px;
        ">
          ✅
        </div>

        <h2>
          Feedback Submitted Successfully
        </h2>

        <p>
          This has been saved as a new feedback record.
        </p>

        <div class="info-panel">
          <b>Feedback ID</b>
          <h2>#${feedbackId}</h2>
          <p>Status: SUBMITTED</p>
        </div>

        <button
          class="primary wide"
          onclick="closeModal()"
        >
          Done
        </button>

      </div>
    `;

    $('modal').classList.remove('hidden');

    farmerFeedbackSubmitting = false;

  }

   catch (e) {

    console.error(
      'Farmer feedback submission failed:',
      e
    );

    farmerFeedbackSubmitting = false;

    const submitBtn =
      document.querySelector('.ff-submit-btn');

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Feedback →';
    }

    toast(
      e.message ||
      'Could not submit feedback'
    );

  }

}
async function buyerFeedbackPage() {

  let orders = [];
  let history = [];

  try {
    orders = await api('/api/orders');

    if (!Array.isArray(orders)) {
      orders = [];
    }
  } catch (e) {
    console.warn('Could not load buyer orders:', e);
  }

  try {
    history = await api('/api/v2/feedback');

    if (!Array.isArray(history)) {
      history = [];
    }
  } catch (e) {
    console.warn('Could not load buyer feedback:', e);
  }


  const historyHtml =
    history.length

      ? history.map(f => `

          <div class="farmer-feedback-order">

            <div class="ff-order-main">

              <div class="ff-order-icon">
                💬
              </div>

              <div>

                <b>
                  Buyer Feedback #${Number(f.id)}
                </b>

                <small>
                  ${
                    f.created_at
                      ? new Date(f.created_at)
                          .toLocaleString('en-IN')
                      : '—'
                  }
                </small>

                <p style="
                  margin:6px 0 0;
                  color:#4b6354;
                ">
                  ${esc(
                    f.message ||
                    'Buyer feedback submitted'
                  )}
                </p>

              </div>

            </div>


            <span class="tag">
              ${esc(
                f.review_status ||
                f.status ||
                'SUBMITTED'
              )}
            </span>

          </div>

        `).join('')

      : `

        <div class="ff-empty">

          <div class="ff-empty-icon">
            🛒
          </div>

          <b>No buyer feedback submitted yet</b>

          <p>
            Share your procurement, farmer,
            logistics or order experience below.
          </p>

        </div>

      `;


  const orderHtml =
    orders.length

      ? orders.slice(0, 6).map(o => `

          <div class="farmer-feedback-order">

            <div class="ff-order-main">

              <div class="ff-order-icon">
                📦
              </div>

              <div>

                <b>
                  Order #${Number(o.id)}
                  •
                  ${esc(o.crop || 'Crop')}
                </b>

                <small>
                  ${esc(o.status || '—')}
                  •
                  ${fmt(o.total || 0)}
                </small>

              </div>

            </div>


            <button
              class="secondary"
              onclick="openOrderFeedback(${Number(o.id)})"
            >
              ⭐ Rate Order
            </button>

          </div>

        `).join('')

      : `

        <div class="ff-empty">

          <div class="ff-empty-icon">
            📦
          </div>

          <b>No orders available for rating</b>

          <p>
            Completed procurement orders will
            appear here for detailed feedback.
          </p>

        </div>

      `;


  $('content').innerHTML = `

    <div class="farmer-feedback-page">


      <div class="ff-hero">

        <div class="ff-hero-copy">

          <span class="ff-eyebrow">
            🛒 Buyer Voice
          </span>

          <h2>
            Help Improve GRAM AI Procurement
          </h2>

          <p>
            Tell us about harvest quality,
            farmer reliability, logistics,
            payments and your overall buying
            experience.
          </p>


          <div class="ff-hero-tags">

            <span>
              ✅ Verified Procurement
            </span>

            <span>
              🤝 Seller Experience
            </span>

            <span>
              🚚 Logistics Feedback
            </span>

            <span>
              💳 Payment Experience
            </span>

          </div>

        </div>


        <div class="ff-impact-card">

          <span style="font-size:30px;">
            🛒
          </span>

          <h3>
            Buyer Co-Design
          </h3>

          <p>
            Your feedback helps improve
            sourcing, seller matching and
            procurement reliability.
          </p>

        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              ⚡
            </span>

            <div>

              <h3>
                Procurement Experience Check
              </h3>

              <p>
                Rate the main parts of your
                GRAM AI buying experience.
              </p>

            </div>

          </div>

        </div>


        <div class="ff-rating-grid">

          ${buyerFeedbackRatingCard(
            'quality',
            '🔍',
            'Harvest Quality',
            'Did produce match the promised grade?'
          )}

          ${buyerFeedbackRatingCard(
            'seller',
            '👨‍🌾',
            'Farmer Reliability',
            'Was the farmer reliable and responsive?'
          )}

          ${buyerFeedbackRatingCard(
            'fulfilment',
            '📦',
            'Order Fulfilment',
            'Was quantity and timing correct?'
          )}

          ${buyerFeedbackRatingCard(
            'logistics',
            '🚚',
            'Logistics',
            'Pickup, delivery and transport experience'
          )}

          ${buyerFeedbackRatingCard(
            'payment',
            '💳',
            'Payment Flow',
            'Was the payment process transparent?'
          )}

          ${buyerFeedbackRatingCard(
            'usability',
            '📱',
            'Ease of Procurement',
            'Was GRAM AI simple to use?'
          )}

        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              🧠
            </span>

            <div>

              <h3>
                Seller Matching & Procurement
              </h3>

              <p>
                Tell us whether GRAM AI helped
                you source the right produce.
              </p>

            </div>

          </div>

          <span class="ff-innovation-badge">
            Buyer Intelligence Feedback
          </span>

        </div>


        <div class="ff-form-grid">

          <div class="field">

            <label>
              Did GRAM AI help you find the right farmer?
            </label>

            <select
              id="bfMatchUseful"
              class="control"
            >
              <option value="">
                Select
              </option>

              <option value="YES">
                Yes
              </option>

              <option value="PARTLY">
                Partly
              </option>

              <option value="NO">
                No
              </option>
            </select>

          </div>


          <div class="field">

            <label>
              Did the produce meet expected quality?
            </label>

            <select
              id="bfQualityOutcome"
              class="control"
            >
              <option value="">
                Select
              </option>

              <option value="BETTER">
                Better than expected
              </option>

              <option value="MATCHED">
                Matched expectation
              </option>

              <option value="LOWER">
                Lower than expected
              </option>
            </select>

          </div>


          <div class="field">

            <label>
              Expected procurement price / qtl
            </label>

            <input
              id="bfExpectedPrice"
              class="control"
              type="number"
              min="0"
              placeholder="₹ Expected price"
            >

          </div>


          <div class="field">

            <label>
              Actual procurement price / qtl
            </label>

            <input
              id="bfActualPrice"
              class="control"
              type="number"
              min="0"
              placeholder="₹ Actual price"
            >

          </div>

        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              🗳️
            </span>

            <div>

              <h3>
                What Should GRAM AI Improve for Buyers?
              </h3>

              <p>
                Vote for the procurement capability
                you want improved next.
              </p>

            </div>

          </div>

          <span class="ff-innovation-badge">
            Buyer Co-Design
          </span>

        </div>


        <div class="ff-vote-grid">

          ${buyerFeedbackVoteCard(
            'supplier_match',
            '🎯',
            'AI Supplier Matcher',
            'Match buyers with verified farmers by crop, quality, quantity and delivery date.'
          )}

          ${buyerFeedbackVoteCard(
            'quality_risk',
            '🔍',
            'Quality Risk Predictor',
            'Estimate quality and fulfilment risk before placing an order.'
          )}

          ${buyerFeedbackVoteCard(
            'demand_planner',
            '📊',
            'Procurement Demand Planner',
            'Plan future crop requirements using demand and price trends.'
          )}

          ${buyerFeedbackVoteCard(
            'logistics_pool',
            '🚛',
            'Buyer Logistics Pool',
            'Combine procurement routes with nearby buyers to reduce logistics cost.'
          )}

        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              💬
            </span>

            <div>

              <h3>
                Tell Us About Your Buying Experience
              </h3>

              <p>
                Share a sourcing issue, idea,
                procurement requirement or experience.
              </p>

            </div>

          </div>

        </div>


        <div class="ff-feedback-box">


          <div class="ff-form-grid">

            <div class="field">

              <label>
                Feedback Type
              </label>

              <select
                id="buyerFeedbackCat"
                class="control"
              >

                <option value="BUYER_FEEDBACK">
                  General Buyer Feedback
                </option>

                <option value="PROCUREMENT">
                  Procurement
                </option>

                <option value="FARMER">
                  Farmer / Seller
                </option>

                <option value="QUALITY">
                  Produce Quality
                </option>

                <option value="LOGISTICS">
                  Logistics
                </option>

                <option value="PAYMENT">
                  Payment
                </option>

                <option value="FEATURE_REQUEST">
                  Feature Request
                </option>

              </select>

            </div>


            <div class="field">

              <label>
                Overall GRAM AI Rating
              </label>

              <select
                id="buyerFeedbackRating"
                class="control"
              >

                <option value="5">
                  ⭐⭐⭐⭐⭐ Excellent
                </option>

                <option value="4">
                  ⭐⭐⭐⭐ Good
                </option>

                <option value="3">
                  ⭐⭐⭐ Average
                </option>

                <option value="2">
                  ⭐⭐ Needs Improvement
                </option>

                <option value="1">
                  ⭐ Poor
                </option>

              </select>

            </div>

          </div>


          <div class="field">

            <label>
              Your feedback / requirement
            </label>

            <div class="ff-voice-input">

              <textarea
                id="buyerFeedbackMsg"
                class="control"
                rows="5"
                placeholder="Example: I need a better way to compare verified farmers by quality, price and delivery reliability..."
              ></textarea>

              <button
                type="button"
                class="ff-mic"
                onclick="voiceInto('buyerFeedbackMsg')"
              >
                🎙
              </button>

            </div>

          </div>



          <div class="ff-options-row">

            <label class="ff-check">

              <input
                id="buyerFeedbackAnonymous"
                type="checkbox"
              >

              Submit anonymously to analytics

            </label>


            <label class="ff-check">

              <input
                id="buyerFeedbackCallback"
                type="checkbox"
              >

              Request support callback

            </label>

          </div>



          <div class="ff-submit-row">

            <div>

              <b>
                🛒 Better procurement through buyer feedback
              </b>

              <small>
                Verified feedback can improve
                sourcing and matching workflows.
              </small>

            </div>


            <button
              class="primary"
              onclick="sendAdvancedBuyerFeedback()"
            >
              Submit Buyer Feedback →
            </button>

          </div>

        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              📦
            </span>

            <div>

              <h3>
                Rate Your Orders
              </h3>

              <p>
                Provide feedback on completed
                farmer transactions.
              </p>

            </div>

          </div>

        </div>

        <div class="ff-order-list">
          ${orderHtml}
        </div>

      </div>



      <div class="ff-section">

        <div class="ff-section-head">

          <div>

            <span class="ff-section-icon">
              📌
            </span>

            <div>

              <h3>
                My Buyer Feedback
              </h3>

              <p>
                Each submission is stored separately.
              </p>

            </div>

          </div>

          <span class="ff-innovation-badge">
            ${history.length}
            Submission${history.length === 1 ? '' : 's'}
          </span>

        </div>


        <div class="ff-order-list">
          ${historyHtml}
        </div>

      </div>


    </div>

  `;

}

function buyerFeedbackRatingCard(
  key,
  icon,
  title,
  subtitle
) {

  return `

    <div class="ff-rating-card">

      <span class="ff-rating-icon">
        ${icon}
      </span>

      <div>

        <b>
          ${esc(title)}
        </b>

        <small>
          ${esc(subtitle)}
        </small>

      </div>


      <input
        id="bfRating_${esc(key)}"
        type="hidden"
        value="0"
      >


      <div
        class="ff-stars"
        data-buyer-feedback-key="${esc(key)}"
      >

        ${[1,2,3,4,5].map(n => `

          <button
            type="button"
            class="ff-star"
            data-value="${n}"
            onclick="
              setBuyerFeedbackRating(
                '${esc(key)}',
                ${n}
              )
            "
          >
            ★
          </button>

        `).join('')}

      </div>

    </div>

  `;

}


function setBuyerFeedbackRating(
  key,
  value
) {

  const input =
    $(`bfRating_${key}`);

  if (input) {
    input.value = value;
  }


  const box =
    document.querySelector(
      `[data-buyer-feedback-key="${key}"]`
    );

  if (!box) {
    return;
  }


  box
    .querySelectorAll('.ff-star')
    .forEach(star => {

      star.classList.toggle(
        'selected',
        Number(star.dataset.value) <= value
      );

    });

}


function buyerFeedbackVoteCard(
  value,
  icon,
  title,
  description
) {

  return `

    <label class="ff-vote-card">

      <input
        type="radio"
        name="buyerFeatureVote"
        value="${esc(value)}"
      >

      <span class="ff-vote-icon">
        ${icon}
      </span>

      <div>

        <b>
          ${esc(title)}
        </b>

        <p>
          ${esc(description)}
        </p>

      </div>

      <span class="ff-vote-check">
        ✓
      </span>

    </label>

  `;

}
let buyerFeedbackSubmitting = false;


async function sendAdvancedBuyerFeedback() {

  if (buyerFeedbackSubmitting) {
    return;
  }

  buyerFeedbackSubmitting = true;


  try {

    const message =
      $('buyerFeedbackMsg')?.value?.trim() || '';

    const category =
      $('buyerFeedbackCat')?.value ||
      'BUYER_FEEDBACK';

    const rating =
      Number(
        $('buyerFeedbackRating')?.value || 5
      );


    const sellerRating =
      Number(
        $('bfRating_seller')?.value || 0
      );

    const qualityRating =
      Number(
        $('bfRating_quality')?.value || 0
      );

    const fulfilmentRating =
      Number(
        $('bfRating_fulfilment')?.value || 0
      );

    const logisticsRating =
      Number(
        $('bfRating_logistics')?.value || 0
      );

    const paymentRating =
      Number(
        $('bfRating_payment')?.value || 0
      );

    const usabilityRating =
      Number(
        $('bfRating_usability')?.value || 0
      );


    const featureVote =
      document.querySelector(
        'input[name="buyerFeatureVote"]:checked'
      )?.value || '';


    const matchUseful =
      $('bfMatchUseful')?.value || '';

    const qualityOutcome =
      $('bfQualityOutcome')?.value || '';

    const expectedPrice =
      Number(
        $('bfExpectedPrice')?.value || 0
      );

    const actualPrice =
      Number(
        $('bfActualPrice')?.value || 0
      );


    const anonymous =
      Boolean(
        $('buyerFeedbackAnonymous')?.checked
      );

    const callbackRequested =
      Boolean(
        $('buyerFeedbackCallback')?.checked
      );


    const details = [];

    if (matchUseful) {
      details.push(
        `Seller matching useful: ${matchUseful}`
      );
    }

    if (qualityOutcome) {
      details.push(
        `Quality outcome: ${qualityOutcome}`
      );
    }

    if (expectedPrice > 0) {
      details.push(
        `Expected procurement price: ₹${expectedPrice}`
      );
    }

    if (actualPrice > 0) {
      details.push(
        `Actual procurement price: ₹${actualPrice}`
      );
    }


    const finalMessage =
      [
        message,
        ...details
      ]
      .filter(Boolean)
      .join('\n');


    const hasAnyInput =
      Boolean(
        message ||
        featureVote ||
        matchUseful ||
        qualityOutcome ||
        sellerRating ||
        qualityRating ||
        fulfilmentRating ||
        logisticsRating ||
        paymentRating ||
        usabilityRating
      );


    if (!hasAnyInput) {
      throw new Error(
        'Please enter buyer feedback, rating or feature vote.'
      );
    }


    const result =
      await api(
        '/api/v2/feedback',
        {
          method: 'POST',

          body: JSON.stringify({

            category,

            rating,

            message:
              finalMessage ||
              'Buyer feedback submitted through GRAM AI',

            voice_transcript: '',

            buyer_experience_rating:
              sellerRating,

            quality_grade_rating:
              qualityRating,

            transport_rating:
              logisticsRating,

            payment_rating:
              paymentRating,

            ease_of_use_rating:
              usabilityRating,

            price_forecast_rating:
              fulfilmentRating,

            recommendation_followed:
              matchUseful,

            recommendation_useful:
              qualityOutcome,

            expected_price:
              expectedPrice,

            actual_selling_price:
              actualPrice,

            alternative_price: 0,

            outcome:
              qualityOutcome,

            local_requirements: [],

            feature_votes:
              featureVote
                ? [featureVote]
                : [],

            anonymous,

            callback_requested:
              callbackRequested

          })

        }
      );


    const feedbackId =
      result.feedback_id ||
      result.id;


    toast(
      `✅ Buyer Feedback #${feedbackId} submitted`
    );


    buyerFeedbackSubmitting = false;

    await buyerFeedbackPage();


    $('modalBody').innerHTML = `

      <div style="
        text-align:center;
        padding:24px;
      ">

        <div style="font-size:50px;">
          ✅
        </div>

        <h2>
          Buyer Feedback Submitted
        </h2>

        <p>
          Your procurement feedback has
          been recorded separately.
        </p>

        <div class="info-panel">

          <b>
            Feedback ID
          </b>

          <h2>
            #${feedbackId}
          </h2>

          <p>
            Status: SUBMITTED
          </p>

        </div>

        <button
          class="primary wide"
          onclick="closeModal()"
        >
          Done
        </button>

      </div>

    `;

    $('modal').classList.remove('hidden');


  } catch (e) {

    buyerFeedbackSubmitting = false;

    console.error(
      'Buyer feedback failed:',
      e
    );

    toast(
      e.message ||
      'Could not submit buyer feedback'
    );

  }

}




function openOrderFeedback(id){$('modalBody').innerHTML=`<h2>Order #${id} Feedback</h2><label>Target</label><select id="ofTarget" class="control"><option value="${me.role==='farmer'?'BUYER':'FARMER'}">${me.role==='farmer'?'Buyer':'Farmer'}</option><option value="TRANSPORT">Transport</option></select><label>Rating</label><select id="ofRating" class="control"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select><label>Comments</label><textarea id="ofComments" class="control"></textarea><button class="primary wide" onclick="submitOrderFeedback(${id})">Submit</button>`;$('modal').classList.remove('hidden')}
async function submitOrderFeedback(id){try{await api(`/api/v2/v3/orders/${id}/feedback`,{method:'POST',body:JSON.stringify({target_type:$('ofTarget').value,rating:+$('ofRating').value,comments:$('ofComments').value})});closeModal();toast('Feedback recorded')}catch(e){toast(e.message)}}
async function farmerGrievancePage() {

  let grievances = [];

  try {
    grievances = await api('/api/v2/grievances');

    if (!Array.isArray(grievances)) {
      grievances = [];
    }

  } catch (e) {

    console.error(
      'Could not load grievances:',
      e
    );

    grievances = [];
  }


  // =========================================================
  // SUMMARY COUNTS
  // =========================================================

  const totalCases =
    grievances.length;

  const openCases =
    grievances.filter(g =>
      ![
        'RESOLVED',
        'CLOSED'
      ].includes(
        String(g.status || '').toUpperCase()
      )
    ).length;

  const resolvedCases =
    grievances.filter(g =>
      [
        'RESOLVED',
        'CLOSED'
      ].includes(
        String(g.status || '').toUpperCase()
      )
    ).length;

  const criticalCases =
    grievances.filter(g =>
      String(
        g.severity || ''
      ).toUpperCase() === 'CRITICAL'
    ).length;


  // =========================================================
  // CASE CARDS
  // =========================================================

  const caseHtml =
    grievances.length

      ? grievances.map(g => {

          const status =
            String(
              g.status || 'OPEN'
            ).toUpperCase();

          const severity =
            String(
              g.severity || 'LOW'
            ).toUpperCase();

          const createdDate =
            g.created_at
              ? new Date(
                  g.created_at
                ).toLocaleString(
                  'en-IN'
                )
              : 'Recently created';

          const statusIcon = {
            OPEN: '🟠',
            SUBMITTED: '🟠',
            REVIEWING: '🔵',
            IN_REVIEW: '🔵',
            ESCALATED: '🔴',
            RESOLVED: '🟢',
            CLOSED: '✅'
          }[status] || '🟡';

          const severityIcon = {
            LOW: '🟢',
            MEDIUM: '🟡',
            HIGH: '🟠',
            CRITICAL: '🔴'
          }[severity] || '🟡';


          return `

            <div class="gr-case-card">

              <div class="gr-case-main">

                <div class="gr-case-top">

                  <div class="gr-case-number">

                    <span class="gr-case-icon">
                      🛡️
                    </span>

                    <div>

                      <small>
                        GramRakshak Case
                      </small>

                      <h3>
                        #${Number(g.id)}
                        •
                        ${esc(
                          String(
                            g.category || 'OTHER'
                          )
                          .replaceAll('_', ' ')
                        )}
                      </h3>

                    </div>

                  </div>


                  <div class="gr-case-tags">

                    <span
                      class="
                        gr-severity
                        gr-severity-${severity.toLowerCase()}
                      "
                    >
                      ${severityIcon}
                      ${esc(severity)}
                    </span>

                    <span class="gr-status-tag">
                      ${statusIcon}
                      ${esc(
                        status.replaceAll('_', ' ')
                      )}
                    </span>

                  </div>

                </div>


                <p class="gr-case-description">
                  ${esc(
                    g.description ||
                    'No description provided.'
                  )}
                </p>


                <div class="gr-case-meta">

                  <span>
                    🕒 ${esc(createdDate)}
                  </span>

                  <span>
                    🔐 Case ID #${Number(g.id)}
                  </span>

                </div>


                ${
                  g.ai_recommendation
                    ? `

                      <div class="gr-ai-resolution">

                        <div class="gr-ai-icon">
                          🤖
                        </div>

                        <div>

                          <b>
                            GRAM AI Resolution Assistant
                          </b>

                          <p>
                            ${esc(
                              g.ai_recommendation
                            )}
                          </p>

                        </div>

                      </div>

                    `
                    : `

                      <div class="gr-ai-resolution pending">

                        <div class="gr-ai-icon">
                          🧠
                        </div>

                        <div>

                          <b>
                            AI-assisted review pending
                          </b>

                          <p>
                            GramRakshak will analyse the issue,
                            linked transaction and supporting
                            evidence.
                          </p>

                        </div>

                      </div>

                    `
                }


                ${
                  g.admin_response
                    ? `

                      <div class="gr-admin-response">

                        <b>
                          👨‍💼 GramRakshak Team Response
                        </b>

                        <p>
                          ${esc(
                            g.admin_response
                          )}
                        </p>

                      </div>

                    `
                    : ''
                }

              </div>


              <div class="gr-case-actions">

                <button
                  class="secondary"
                  onclick="attachEvidence(${Number(g.id)})"
                >
                  📎 Attach Evidence
                </button>

              </div>

            </div>

          `;

        }).join('')

      : `

        <div class="gr-empty-state">

          <div class="gr-empty-icon">
            🛡️
          </div>

          <h3>
            No GramRakshak cases yet
          </h3>

          <p>
            If you face a payment, buyer, delivery,
            transport or quality issue, raise a grievance
            above. Your cases will appear here.
          </p>

        </div>

      `;


  // =========================================================
  // PAGE
  // =========================================================

  $('content').innerHTML = `

    <div class="gramrakshak-page">


      <!-- =============================================
           HERO
      ============================================== -->

      <div class="gr-hero">

        <div class="gr-hero-copy">

          <span class="gr-eyebrow">
            🛡️ Farmer Protection
          </span>

          <h1>
            GramRakshak
          </h1>

          <p>
            Raise payment, buyer, transport, delivery,
            cancellation or quality disputes and track
            their resolution securely.
          </p>


          <div class="gr-hero-tags">

            <span>
              🔐 Secure Case Tracking
            </span>

            <span>
              🤖 AI Assisted Review
            </span>

            <span>
              📎 Evidence Support
            </span>

            <span>
              🚨 Escalation Ready
            </span>

          </div>

        </div>


        <div class="gr-protection-card">

          <div class="gr-protection-icon">
            🛡️
          </div>

          <h3>
            Farmer Protection First
          </h3>

          <p>
            Every complaint receives a case ID and can
            be reviewed with transaction and evidence
            history.
          </p>

        </div>

      </div>



      <!-- =============================================
           CASE SUMMARY
      ============================================== -->

      <div class="gr-stats">

        <div class="gr-stat-card">

          <span>📂</span>

          <div>
            <small>Total Cases</small>
            <b>${totalCases}</b>
          </div>

        </div>


        <div class="gr-stat-card">

          <span>⏳</span>

          <div>
            <small>Active Cases</small>
            <b>${openCases}</b>
          </div>

        </div>


        <div class="gr-stat-card">

          <span>✅</span>

          <div>
            <small>Resolved</small>
            <b>${resolvedCases}</b>
          </div>

        </div>


        <div class="gr-stat-card">

          <span>🚨</span>

          <div>
            <small>Critical</small>
            <b>${criticalCases}</b>
          </div>

        </div>

      </div>



      <!-- =============================================
           RAISE GRIEVANCE
      ============================================== -->

      <div class="gr-section">

        <div class="gr-section-head">

          <div class="gr-section-title">

            <span class="gr-section-icon">
              📢
            </span>

            <div>

              <h2>
                Raise a New Grievance
              </h2>

              <p>
                Tell GramRakshak what happened.
                Select the closest issue category.
              </p>

            </div>

          </div>


          <span class="gr-safe-badge">
            🔒 Secure Submission
          </span>

        </div>



        <div class="gr-category-guide">

          <div>
            💳
            <b>Payment</b>
            <small>Delayed or incorrect payment</small>
          </div>

          <div>
            🤝
            <b>Buyer</b>
            <small>Buyer behaviour or commitment</small>
          </div>

          <div>
            🚚
            <b>Transport</b>
            <small>Pickup or logistics issue</small>
          </div>

          <div>
            📦
            <b>Delivery</b>
            <small>Delivery or receiving dispute</small>
          </div>

          <div>
            🔍
            <b>Quality</b>
            <small>Grade or produce dispute</small>
          </div>

          <div>
            ❌
            <b>Cancellation</b>
            <small>Unexpected cancellation</small>
          </div>

        </div>



        <div class="gr-form-card">

          <div class="gr-form-grid">


            <div class="field">

              <label>
                Issue Category
              </label>

              <select
                id="gcat"
                class="control"
              >

                <option value="PAYMENT">
                  💳 Payment
                </option>

                <option value="DELAYED_PAYMENT">
                  ⏳ Delayed Payment
                </option>

                <option value="BUYER_BEHAVIOUR">
                  🤝 Buyer Behaviour
                </option>

                <option value="TRANSPORT">
                  🚚 Transport
                </option>

                <option value="DELIVERY">
                  📦 Delivery
                </option>

                <option value="QUALITY">
                  🔍 Quality / Grade
                </option>

                <option value="CANCELLATION">
                  ❌ Cancellation
                </option>

                <option value="OTHER">
                  📝 Other
                </option>

              </select>

            </div>



            <div class="field">

              <label>
                How urgent is this?
              </label>

              <div class="gr-auto-severity">

                🤖 GramRakshak automatically evaluates
                severity after submission.

              </div>

            </div>



            <div class="field full">

              <label>
                Describe your problem
              </label>

              <div class="gr-voice-box">

                <textarea
                  id="gdesc"
                  class="control"
                  rows="6"
                  maxlength="2000"
                  placeholder="Example: Buyer accepted my Tomato order but payment has not been received after delivery..."
                  oninput="updateGrievanceCounter()"
                ></textarea>


                <button
                  type="button"
                  class="gr-mic"
                  title="Speak your grievance"
                  onclick="voiceInto('gdesc')"
                >
                  🎙️
                </button>

              </div>


              <div class="gr-text-help">

                <span>
                  You can type or speak in your language.
                </span>

                <span id="grCharCount">
                  0 / 2000
                </span>

              </div>

            </div>


          </div>



          <div class="gr-protection-note">

            <span>
              🔐
            </span>

            <div>

              <b>
                Your grievance is securely recorded
              </b>

              <p>
                After submission you can attach
                screenshots, photos, videos or PDF
                evidence to your case.
              </p>

            </div>

          </div>



          <div class="gr-submit-row">

            <div>

              <b>
                🛡️ GramRakshak Protection
              </b>

              <small>
                A unique case ID will be generated
                after submission.
              </small>

            </div>


            <button
              class="primary gr-submit-btn"
              onclick="createGrievance()"
            >
              Submit to GramRakshak →
            </button>

          </div>

        </div>

      </div>



      <!-- =============================================
           MY CASES
      ============================================== -->

      <div class="gr-section">

        <div class="gr-section-head">

          <div class="gr-section-title">

            <span class="gr-section-icon">
              📋
            </span>

            <div>

              <h2>
                My GramRakshak Cases
              </h2>

              <p>
                Track complaint severity, status,
                evidence and resolution.
              </p>

            </div>

          </div>


          <span class="gr-safe-badge">
            ${totalCases}
            Case${totalCases === 1 ? '' : 's'}
          </span>

        </div>


        <div class="gr-case-list">

          ${caseHtml}

        </div>

      </div>


    </div>

  `;

}

function updateGrievanceCounter() {

  const textarea =
    $('gdesc');

  const counter =
    $('grCharCount');

  if (!textarea || !counter) {
    return;
  }

  counter.textContent =
    `${textarea.value.length} / 2000`;
}

async function buyerGrievancePage() {

  let grievances = [];

  try {

    grievances =
      await api('/api/v2/grievances');

    if (!Array.isArray(grievances)) {
      grievances = [];
    }

  } catch (e) {

    console.error(
      'Could not load buyer grievances:',
      e
    );

  }


  const total =
    grievances.length;

  const active =
    grievances.filter(g =>
      ![
        'RESOLVED',
        'CLOSED'
      ].includes(
        String(g.status || '')
          .toUpperCase()
      )
    ).length;

  const resolved =
    grievances.filter(g =>
      [
        'RESOLVED',
        'CLOSED'
      ].includes(
        String(g.status || '')
          .toUpperCase()
      )
    ).length;

  const critical =
    grievances.filter(g =>
      String(g.severity || '')
        .toUpperCase() === 'CRITICAL'
    ).length;


  const caseHtml =
    grievances.length

      ? grievances.map(g => `

          <div class="gr-case-card">

            <div class="gr-case-top">

              <div class="gr-case-number">

                <span class="gr-case-icon">
                  🛡️
                </span>

                <div>

                  <small>
                    Buyer Protection Case
                  </small>

                  <h3>
                    #${Number(g.id)}
                    •
                    ${esc(
                      String(
                        g.category ||
                        'OTHER'
                      ).replaceAll('_',' ')
                    )}
                  </h3>

                </div>

              </div>


              <div class="gr-case-tags">

                <span
                  class="
                    gr-severity
                    gr-severity-${
                      String(
                        g.severity ||
                        'LOW'
                      ).toLowerCase()
                    }
                  "
                >
                  ${esc(
                    g.severity ||
                    'LOW'
                  )}
                </span>

                <span class="gr-status-tag">
                  ${esc(
                    g.status ||
                    'OPEN'
                  )}
                </span>

              </div>

            </div>


            <p class="gr-case-description">
              ${esc(
                g.description ||
                'No description provided.'
              )}
            </p>


            <div class="gr-ai-resolution">

              <div class="gr-ai-icon">
                🤖
              </div>

              <div>

                <b>
                  Buyer Protection Assistant
                </b>

                <p>
                  ${esc(
                    g.ai_recommendation ||
                    'GRAM AI will analyse the seller, order, payment and evidence history.'
                  )}
                </p>

              </div>

            </div>


            <div class="gr-case-actions">

              <button
                class="secondary"
                onclick="attachEvidence(${Number(g.id)})"
              >
                📎 Attach Evidence
              </button>

            </div>

          </div>

        `).join('')

      : `

        <div class="gr-empty-state">

          <div class="gr-empty-icon">
            🛒
          </div>

          <h3>
            No buyer protection cases
          </h3>

          <p>
            Report seller, quality, fulfilment,
            logistics, payment or refund issues here.
          </p>

        </div>

      `;


  $('content').innerHTML = `

    <div class="gramrakshak-page">


      <div class="gr-hero">

        <div class="gr-hero-copy">

          <span class="gr-eyebrow">
            🛒 Buyer Protection
          </span>

          <h1>
            GramRakshak for Buyers
          </h1>

          <p>
            Report seller cancellations,
            quality mismatch, quantity issues,
            delayed dispatch, logistics problems,
            payments or refunds.
          </p>


          <div class="gr-hero-tags">

            <span>
              👨‍🌾 Seller Protection
            </span>

            <span>
              🔍 Quality Disputes
            </span>

            <span>
              📦 Fulfilment Protection
            </span>

            <span>
              💳 Payment & Refund Support
            </span>

          </div>

        </div>


        <div class="gr-protection-card">

          <div class="gr-protection-icon">
            🛒
          </div>

          <h3>
            Procurement Protection
          </h3>

          <p>
            Buyer complaints can be reviewed
            with linked order, payment and
            evidence records.
          </p>

        </div>

      </div>



      <div class="gr-stats">

        <div class="gr-stat-card">
          <span>📂</span>
          <div>
            <small>Total Cases</small>
            <b>${total}</b>
          </div>
        </div>

        <div class="gr-stat-card">
          <span>⏳</span>
          <div>
            <small>Active</small>
            <b>${active}</b>
          </div>
        </div>

        <div class="gr-stat-card">
          <span>✅</span>
          <div>
            <small>Resolved</small>
            <b>${resolved}</b>
          </div>
        </div>

        <div class="gr-stat-card">
          <span>🚨</span>
          <div>
            <small>Critical</small>
            <b>${critical}</b>
          </div>
        </div>

      </div>



      <div class="gr-section">

        <div class="gr-section-head">

          <div class="gr-section-title">

            <span class="gr-section-icon">
              📢
            </span>

            <div>

              <h2>
                Raise Buyer Grievance
              </h2>

              <p>
                Report a problem related to
                procurement or farmer fulfilment.
              </p>

            </div>

          </div>

          <span class="gr-safe-badge">
            🔒 Buyer Protection
          </span>

        </div>



        <div class="gr-category-guide">

          <div>
            👨‍🌾
            <b>Seller</b>
            <small>Farmer commitment issue</small>
          </div>

          <div>
            🔍
            <b>Quality</b>
            <small>Grade mismatch</small>
          </div>

          <div>
            ⚖️
            <b>Quantity</b>
            <small>Quantity mismatch</small>
          </div>

          <div>
            📦
            <b>Fulfilment</b>
            <small>Delayed or failed dispatch</small>
          </div>

          <div>
            🚚
            <b>Logistics</b>
            <small>Pickup or delivery problem</small>
          </div>

          <div>
            💳
            <b>Payment</b>
            <small>Refund or transaction issue</small>
          </div>

        </div>



        <div class="gr-form-card">

          <div class="gr-form-grid">

            <div class="field">

              <label>
                Issue Category
              </label>

              <select
                id="gcat"
                class="control"
              >

                <option value="SELLER_BEHAVIOUR">
                  👨‍🌾 Seller Behaviour
                </option>

                <option value="QUALITY">
                  🔍 Quality / Grade Mismatch
                </option>

                <option value="QUANTITY_MISMATCH">
                  ⚖️ Quantity Mismatch
                </option>

                <option value="DELAYED_DISPATCH">
                  ⏳ Delayed Dispatch
                </option>

                <option value="CANCELLATION">
                  ❌ Farmer Cancellation
                </option>

                <option value="TRANSPORT">
                  🚚 Logistics / Transport
                </option>

                <option value="PAYMENT">
                  💳 Payment
                </option>

                <option value="REFUND">
                  ↩️ Refund
                </option>

                <option value="OTHER">
                  📝 Other
                </option>

              </select>

            </div>


            <div class="field">

              <label>
                Severity
              </label>

              <div class="gr-auto-severity">
                🤖 GRAM AI automatically determines
                urgency from the complaint.
              </div>

            </div>


            <div class="field full">

              <label>
                Describe the procurement problem
              </label>

              <div class="gr-voice-box">

                <textarea
                  id="gdesc"
                  class="control"
                  rows="6"
                  maxlength="2000"
                  placeholder="Example: The farmer promised Grade A Tomato but the delivered produce did not match the verified grade..."
                  oninput="updateGrievanceCounter()"
                ></textarea>

                <button
                  type="button"
                  class="gr-mic"
                  onclick="voiceInto('gdesc')"
                >
                  🎙️
                </button>

              </div>


              <div class="gr-text-help">

                <span>
                  Add the important order or seller details.
                </span>

                <span id="grCharCount">
                  0 / 2000
                </span>

              </div>

            </div>

          </div>


          <div class="gr-protection-note">

            <span>
              🔐
            </span>

            <div>

              <b>
                Procurement complaint protection
              </b>

              <p>
                After submission you can attach
                product photos, invoices,
                screenshots, videos or PDFs.
              </p>

            </div>

          </div>


          <div class="gr-submit-row">

            <div>

              <b>
                🛒 Buyer Protection Case
              </b>

              <small>
                A unique GramRakshak case ID
                will be generated.
              </small>

            </div>

            <button
              class="primary gr-submit-btn"
              onclick="createGrievance()"
            >
              Submit Buyer Grievance →
            </button>

          </div>

        </div>

      </div>



      <div class="gr-section">

        <div class="gr-section-head">

          <div class="gr-section-title">

            <span class="gr-section-icon">
              📋
            </span>

            <div>

              <h2>
                My Buyer Protection Cases
              </h2>

              <p>
                Track complaint status,
                severity and evidence.
              </p>

            </div>

          </div>

          <span class="gr-safe-badge">
            ${total}
            Case${total === 1 ? '' : 's'}
          </span>

        </div>

        <div class="gr-case-list">
          ${caseHtml}
        </div>

      </div>


    </div>

  `;

}

async function createGrievance() {

  try {

    const category =
      $('gcat')?.value || 'OTHER';

    const description =
      $('gdesc')?.value?.trim() || '';

    if (!description) {
      throw new Error(
        'Please describe your grievance.'
      );
    }

    const result =
      await api(
        '/api/v2/grievances',
        {
          method: 'POST',

          body: JSON.stringify({
            category,
            description
          })
        }
      );

    toast(
      `🛡️ GramRakshak case created${
        result?.id
          ? ` #${result.id}`
          : ''
      }`
    );

    if (me.role === 'buyer') {

      await buyerGrievancePage();

    } else {

      await farmerGrievancePage();

    }

  } catch (e) {

    console.error(
      'Grievance submission failed:',
      e
    );

    toast(
      e.message ||
      'Could not create grievance'
    );

  }

}



function attachEvidence(id){$('modalBody').innerHTML=`<h2>Evidence for grievance #${id}</h2><input id="evFile" class="control" type="file" accept="image/*,video/*,.pdf" capture="environment"><button class="primary wide" onclick="uploadEvidence(${id})">Upload evidence</button>`;$('modal').classList.remove('hidden')}
async function uploadEvidence(id){try{let f=$('evFile').files[0];if(!f)throw Error('Choose evidence');let fd=new FormData();fd.append('file',f);await api(`/api/v2/grievances/${id}/evidence`,{method:'POST',body:fd});closeModal();toast('Evidence attached securely')}catch(e){toast(e.message)}}

const LINK_INDIA_STATES = [

  'Maharashtra',
  'Gujarat',
  'Punjab',
  'Rajasthan',
  'Karnataka',
  'Tamil Nadu',
  'Telangana',
  'Andhra Pradesh',
  'Madhya Pradesh',
  'Uttar Pradesh',
  'Haryana',
  'Bihar',
  'West Bengal',
  'Odisha',
  'Chhattisgarh',
  'Jharkhand',
  'Kerala',
  'Assam',
  'Uttarakhand',
  'Himachal Pradesh',
  'Goa',
  'Arunachal Pradesh',
  'Meghalaya',
  'Manipur',
  'Mizoram',
  'Nagaland',
  'Tripura',
  'Sikkim'
];


const LINK_INDIA_STATE_ICONS = {

  'Maharashtra': '🍅',
  'Gujarat': '🌾',
  'Punjab': '🌾',
  'Rajasthan': '🌿',
  'Karnataka': '🌽',
  'Tamil Nadu': '🍌',
  'Telangana': '🌶️',
  'Andhra Pradesh': '🥭',
  'Madhya Pradesh': '🌱',
  'Uttar Pradesh': '🥔',
  'Haryana': '🌾',
  'Bihar': '🌽',
  'West Bengal': '🥔',
  'Odisha': '🌾',
  'Chhattisgarh': '🌾',
  'Jharkhand': '🥬',
  'Kerala': '🥥',
  'Assam': '🍃',
  'Uttarakhand': '🍎',
  'Himachal Pradesh': '🍎',
  'Goa': '🥥',
  'Arunachal Pradesh': '🌱',
  'Meghalaya': '🍍',
  'Manipur': '🌾',
  'Mizoram': '🌱',
  'Nagaland': '🌶️',
  'Tripura': '🍍',
  'Sikkim': '🌿'

};


async function networkPage(role) {

  try {

    $('content').innerHTML = `

      <div class="link-india-page">


        <div class="link-india-hero">


          <div>

            <span class="link-india-label">
              🇮🇳 GRAM AI National Network
            </span>


            <h1>
              Link India
            </h1>


            <p>
              Explore agricultural markets, verified farmers,
              produce availability and selling opportunities
              across India.
            </p>

          </div>


          <div class="india-network-badge">

            <span>🇮🇳</span>

            <div>
              <b>Pan India</b>
              <small>Agricultural Network</small>
            </div>

          </div>


        </div>



        <div class="link-india-section-head">

          <div>

            <h2>
              🇮🇳 India Market Prices
            </h2>

            <p>
              Search any crop for today's highest and lowest mandi price across India.
            </p>

          </div>

        </div>

        <div class="crop-price-search">
          <input
            id="cropPriceInput"
            class="control"
            type="text"
            placeholder="Enter crop name... e.g. Tomato"
            onkeydown="if(event.key==='Enter')searchCropPrice()"
          >
          <button class="primary" onclick="searchCropPrice()">
            Search
          </button>
        </div>

        <div id="cropPriceResult" class="crop-price-result"></div>



        <div class="link-india-stats">

          <div class="india-stat-card">

            <span>🗺️</span>

            <div>
              <small>States Covered</small>
              <b>${LINK_INDIA_STATES.length}+</b>
            </div>

          </div>


          <div class="india-stat-card">

            <span>🌾</span>

            <div>
              <small>Market Network</small>
              <b>All India</b>
            </div>

          </div>


          <div class="india-stat-card">

            <span>🤝</span>

            <div>
              <small>Farmer Network</small>
              <b>Connected</b>
            </div>

          </div>


          <div class="india-stat-card">

            <span>🚚</span>

            <div>
              <small>Cross-State</small>
              <b>Trade Ready</b>
            </div>

          </div>


        </div>



        <div class="link-india-section-head">

          <div>

            <h2>
              Explore India by State
            </h2>

            <p>
              Select a state to open its complete market page.
            </p>

          </div>

        </div>



        <div class="india-state-grid">

          ${LINK_INDIA_STATES.map(state => `

            <button
  type="button"
  class="india-state-card"
  data-state="${esc(state)}"
  onclick="openStateMarketPage('${state.replace(/'/g, "\\'")}','${role}')"
>


              <div class="state-card-icon">

                ${
                  LINK_INDIA_STATE_ICONS[state]
                  || '🌾'
                }

              </div>


              <div>

                <h3>
                  ${esc(state)}
                </h3>

                <p>
                  View markets & produce
                </p>

              </div>


              <span class="state-arrow">
                →
              </span>


            </button>

          `).join('')}

        </div>



        <div class="link-india-section-head trending-heading">

          <div>

            <span class="trending-label">
              🔥 LIVE OPPORTUNITIES
            </span>

            <h2>
              Top 5 Trending Markets in India
            </h2>

            <p>
              Markets with strong network activity,
              available produce and trading volume.
            </p>

          </div>

        </div>


        <div
          id="trendingIndiaMarkets"
          class="trending-market-grid"
        >

          <div class="empty">
            Loading trending markets...
          </div>

        </div>



        <div class="link-india-section-head">

          <div>

            <h2>
              India Network Map
            </h2>

            <p>
              View agricultural network participants
              across India.
            </p>

          </div>

        </div>


        <div
          id="indiaMap"
          class="network-map link-india-map"
        ></div>


      </div>

    `;


    setTimeout(
      () => loadIndiaOverview(role),
      50
    );


  }

  catch (e) {

    toast(e.message);

  }

}

async function loadIndiaOverview(role) {

  try {

    const rows =
      await api(
        `/api/v2/v3/network?role=${role}&state=ALL`
      );


    /* --------------------------------
       INDIA MAP
    -------------------------------- */

    if (mapObj) {

      mapObj.remove();

    }


    mapObj =
      L.map('indiaMap')
       .setView(
         [22.5, 79.5],
         4.6
       );


    L.tileLayer(

      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',

      {
        attribution: '© OpenStreetMap'
      }

    ).addTo(mapObj);



    rows.forEach(x => {

      if (
        x.lat === undefined ||
        x.lon === undefined
      ) return;


      const marker =
        L.marker([
          Number(x.lat),
          Number(x.lon)
        ])
        .addTo(mapObj);


      marker.bindPopup(`

        <div class="map-market-popup">

          <b>
            ${esc(x.name)}
          </b>

          <br>

          ${esc(x.district || '')},
          ${esc(x.state || '')}

          <br>

          ${esc(x.crops || '')}

          <br>

          ★ ${num(x.rating || 0)}

          <br>

          ${
            x.verified
              ? '✓ GRAM Network Verified'
              : ''
          }

          <br><br>

          <button
            onclick="
              openStateMarketPage(
                '${String(x.state || '').replace(/'/g, "\\'")}',
                '${role}'
              )
            "
          >
            View State
          </button>

        </div>

      `);

    });



    /* --------------------------------
       TOP 5 TRENDING
    -------------------------------- */

    renderTrendingMarkets(
      rows,
      role
    );


  }

  catch (e) {

    console.error(e);


    const box =
      $('trendingIndiaMarkets');


    if (box) {

      box.innerHTML = `

        <div class="empty">
          Network data is currently unavailable.
        </div>

      `;

    }

  }

}

function renderTrendingMarkets(rows, role) {

  const container =
    $('trendingIndiaMarkets');


  if (!container) return;



  const stateStats = {};


  rows.forEach(x => {

    const state =
      x.state || 'Unknown';


    if (!stateStats[state]) {

      stateStats[state] = {

        state: state,

        participants: 0,

        volume: 0,

        ratingTotal: 0,

        ratingCount: 0,

        crops: new Set()

      };

    }


    const s =
      stateStats[state];


    s.participants += 1;


    s.volume +=
      Number(x.volume_qtl || 0);


    if (Number(x.rating || 0)) {

      s.ratingTotal +=
        Number(x.rating);

      s.ratingCount += 1;

    }


    String(x.crops || '')
      .split(',')
      .forEach(c => {

        if (c.trim()) {

          s.crops.add(
            c.trim()
          );

        }

      });

  });



  let trending =
    Object.values(stateStats)

      .map(s => ({

        ...s,

        rating:
          s.ratingCount
            ? s.ratingTotal /
              s.ratingCount
            : 0,

        cropCount:
          s.crops.size

      }))

      .sort(

        (a, b) => {

          const aScore =
            a.volume +
            a.participants * 40 +
            a.rating * 50;


          const bScore =
            b.volume +
            b.participants * 40 +
            b.rating * 50;


          return bScore - aScore;

        }

      )

      .slice(0, 5);



  /*
    If demo network data has fewer than
    five represented states, show useful
    fallback state cards without inventing prices.
  */

  const fallbackStates = [

    'Maharashtra',
    'Punjab',
    'Gujarat',
    'Karnataka',
    'Tamil Nadu'

  ];


  fallbackStates.forEach(state => {

    if (
      trending.length < 5 &&
      !trending.some(
        x => x.state === state
      )
    ) {

      trending.push({

        state: state,

        participants: 0,

        volume: 0,

        rating: 0,

        cropCount: 0,

        crops: new Set()

      });

    }

  });



  container.innerHTML =

    trending.map(
      (x, index) => `

        <div
          class="trending-market-card"
          onclick="
            openStateMarketPage(
              '${x.state.replace(/'/g, "\\'")}',
              '${role}'
            )
          "
        >


          <div class="trend-rank">
            #${index + 1}
          </div>


          <div class="trend-state-icon">

            ${
              LINK_INDIA_STATE_ICONS[x.state]
              || '🌾'
            }

          </div>


          <div class="trend-market-info">

            <span>
              ${index === 0
                ? '🔥 Most Active'
                : 'Trending'}
            </span>


            <h3>
              ${esc(x.state)}
            </h3>


            <p>

              ${
                x.cropCount
                  ? `${x.cropCount} crop categories`
                  : 'Explore agricultural markets'
              }

            </p>

          </div>


          <div class="trend-market-stats">

            <span>

              Network

              <b>
                ${x.participants || '—'}
              </b>

            </span>


            <span>

              Volume

              <b>

                ${
                  x.volume
                    ? `${num(x.volume)} qtl`
                    : 'Explore'
                }

              </b>

            </span>


            <span>

              Rating

              <b>

                ${
                  x.rating
                    ? `★ ${num(x.rating)}`
                    : '—'
                }

              </b>

            </span>

          </div>


          <button class="secondary">

            Explore
            →

          </button>


        </div>

      `

    ).join('');

}

/* =========================================================
   LINK INDIA - CROP PRICE SEARCH (live AGMARKNET data)
========================================================= */

async function searchCropPrice() {

  const input = $('cropPriceInput');
  const box = $('cropPriceResult');
  if (!box) return;

  const crop = (input && input.value || '').trim();
  if (!crop) {
    box.innerHTML = `<div class="crop-price-error">Enter a crop name to search.</div>`;
    return;
  }

  box.innerHTML = `<div class="empty">Searching official mandi prices for ${esc(crop)}...</div>`;
  clearStateHighlights();

  try {
    // A manual fetch, not the shared api() helper: this endpoint's error
    // body uses {success:false, message} rather than api()'s {detail}
    // convention, and renderCropPrice() already understands that shape.
    const r = await fetch(`/api/market-prices?crop=${encodeURIComponent(crop)}`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    const d = await r.json();
    renderCropPrice(d);
  } catch (e) {
    box.innerHTML = `<div class="crop-price-error">⚠️ Market price data is temporarily unavailable. Please try again later.</div>`;
  }
}

/* Colours the matching cards in the "Explore India by State" grid below -
   red for the state with the highest price, green for the lowest - so the
   search result is visible on the map of states too, not just the two
   summary boxes. Matching is case-insensitive since state names arrive
   from different sources (live government data vs local seed data). */
function clearStateHighlights() {
  document.querySelectorAll('.india-state-card.state-price-high, .india-state-card.state-price-low')
    .forEach(el => el.classList.remove('state-price-high', 'state-price-low'));
}

function highlightStateCards(highState, lowState) {
  clearStateHighlights();
  const norm = s => (s || '').trim().toLowerCase();
  document.querySelectorAll('.india-state-card[data-state]').forEach(el => {
    const s = norm(el.dataset.state);
    if (s && s === norm(highState)) el.classList.add('state-price-high');
    if (s && s === norm(lowState)) el.classList.add('state-price-low');
  });
}

function renderCropPrice(d) {

  const box = $('cropPriceResult');
  if (!box) return;

  if (!d || d.success === false) {
    box.innerHTML = `<div class="crop-price-error">⚠️ ${esc((d && d.message) || 'No market data found for this crop.')}</div>`;
    clearStateHighlights();
    return;
  }

  const h = d.highest, l = d.lowest;

  const tied = list => (list && list.length)
    ? `<div class="crop-price-tied">+ ${list.length} more market${list.length > 1 ? 's' : ''} at this price</div>`
    : '';

  box.innerHTML = `
    <div class="crop-price-card">

      <div class="crop-price-title">
        🍅 ${esc((d.crop || '').toUpperCase())}
        ${d.is_local_fallback ? '<span class="crop-price-demo-tag">Local demo data</span>' : ''}
      </div>

      <div class="crop-price-grid">

        <div class="crop-price-box crop-price-high">
          <div class="crop-price-label">🔴 HIGHEST PRICE STATE</div>
          <div class="crop-price-state">${esc(h.state)}</div>
          <div class="crop-price-value">${fmt(h.price)} / quintal</div>
          <div class="crop-price-meta">Market: ${esc(h.market)}</div>
          <div class="crop-price-meta">District: ${esc(h.district)}</div>
          ${h.modal_price != null ? `<div class="crop-price-meta">Modal price: ${fmt(h.modal_price)}</div>` : ''}
          ${tied(h.tied_markets)}
        </div>

        <div class="crop-price-box crop-price-low">
          <div class="crop-price-label">🟢 LOWEST PRICE STATE</div>
          <div class="crop-price-state">${esc(l.state)}</div>
          <div class="crop-price-value">${fmt(l.price)} / quintal</div>
          <div class="crop-price-meta">Market: ${esc(l.market)}</div>
          <div class="crop-price-meta">District: ${esc(l.district)}</div>
          ${l.modal_price != null ? `<div class="crop-price-meta">Modal price: ${fmt(l.modal_price)}</div>` : ''}
          ${tied(l.tied_markets)}
        </div>

      </div>

      <div class="crop-price-foot">
        <span>📅 Data date: ${esc(d.date_display || d.date)}${d.is_today ? '' : ' (latest available - not today)'}</span>
        <span>📊 Source: ${esc(d.source)}</span>
      </div>

    </div>
  `;

  highlightStateCards(h.state, l.state);
}

/* =========================================================
   LINK INDIA - STATE PAGE
========================================================= */

async function openStateMarketPage(state, role = 'farmer') {

  console.log(
    'Opening Link India state:',
    state,
    role
  );

  try {

    /*
      IMPORTANT:
      Render the state page FIRST.

      The page must open even when the database
      currently has no records for that state.
    */

    $('content').innerHTML = `

      <div class="state-market-page">


        <!-- =====================================
             BACK TO LINK INDIA
        ====================================== -->

        <div class="state-market-topbar">

          <button
            type="button"
            class="secondary"
            onclick="networkPage('${role}')"
          >
            ← Back to Link India
          </button>

        </div>



        <!-- =====================================
             STATE HERO
        ====================================== -->

        <div class="state-market-hero">


          <div class="state-market-icon">

            ${
              LINK_INDIA_STATE_ICONS[state]
              || '🌾'
            }

          </div>


          <div>

            <span>
              🇮🇳 GRAM AI State Market Network
            </span>


            <h1>
              ${esc(state)}
            </h1>


            <p>

              Explore agricultural markets,
              available produce, verified farmers
              and cross-state opportunities in
              ${esc(state)}.

            </p>

          </div>


        </div>



        <!-- =====================================
             STATE STATISTICS
        ====================================== -->

        <div
          id="stateMarketStats"
          class="link-india-stats"
        >


          <div class="india-stat-card">

            <span>
              🏪
            </span>

            <div>

              <small>
                Markets
              </small>

              <b>
                Loading...
              </b>

            </div>

          </div>



          <div class="india-stat-card">

            <span>
              🌾
            </span>

            <div>

              <small>
                Produce Listings
              </small>

              <b>
                Loading...
              </b>

            </div>

          </div>



          <div class="india-stat-card">

            <span>
              👨‍🌾
            </span>

            <div>

              <small>
                Verified Network
              </small>

              <b>
                Loading...
              </b>

            </div>

          </div>



          <div class="india-stat-card">

            <span>
              📦
            </span>

            <div>

              <small>
                Available Volume
              </small>

              <b>
                Loading...
              </b>

            </div>

          </div>


        </div>



        <!-- =====================================
             MARKETS
        ====================================== -->

        <div class="link-india-section-head">

          <div>

            <h2>
              🏪 Markets in ${esc(state)}
            </h2>


            <p>

              Explore agricultural markets and
              trading opportunities in
              ${esc(state)}.

            </p>

          </div>

        </div>


        <div
          id="stateMarketList"
          class="state-market-grid"
        >

          <div class="empty">

            Loading markets in
            ${esc(state)}...

          </div>

        </div>



        <!-- =====================================
             AVAILABLE PRODUCE
        ====================================== -->

        <div class="link-india-section-head">

          <div>

            <h2>
              🌾 Available Produce
            </h2>


            <p>

              Produce currently available
              from farmers in
              ${esc(state)}.

            </p>

          </div>

        </div>


        <div
          id="stateProduceList"
          class="state-produce-grid"
        >

          <div class="empty">

            Loading available produce...

          </div>

        </div>



        <!-- =====================================
             FARMER / MARKET NETWORK
        ====================================== -->

        <div class="link-india-section-head">

          <div>

            <h2>
              👨‍🌾 Farmer & Market Network
            </h2>


            <p>

              Connect with agricultural
              participants across
              ${esc(state)}.

            </p>

          </div>

        </div>


        <div
          id="stateNetworkList"
          class="network-list"
        >

          <div class="empty">

            Loading network...

          </div>

        </div>



        <!-- =====================================
             STATE MAP
        ====================================== -->

        <div class="link-india-section-head">

          <div>

            <h2>
              📍 ${esc(state)} Market Map
            </h2>


            <p>

              Explore market and farmer
              locations.

            </p>

          </div>

        </div>


        <div
          id="stateIndiaMap"
          class="network-map state-network-map"
        ></div>


      </div>

    `;



    /*
      Page has rendered successfully.

      NOW load state-specific data.
    */

    await loadStateMarketData(
      state,
      role
    );


  }

  catch (e) {

    console.error(
      'State market page error:',
      e
    );


    /*
      Even if one backend API fails,
      we keep the state page visible.
    */

    if ($('stateMarketList')) {

      $('stateMarketList').innerHTML = `

        <div class="empty">

          <h3>
            ${esc(state)} Market Page
          </h3>

          <p>

            The state page opened successfully,
            but market data is not available yet.

          </p>

          <small>

            Market information for this state
            can be added to the GRAM AI database.

          </small>

        </div>

      `;

    }



    if ($('stateProduceList')) {

      $('stateProduceList').innerHTML = `

        <div class="empty">

          No produce data has been added for
          ${esc(state)} yet.

        </div>

      `;

    }



    if ($('stateNetworkList')) {

      $('stateNetworkList').innerHTML = `

        <div class="empty">

          No network participants have been
          added for ${esc(state)} yet.

        </div>

      `;

    }

  }

}



/* =========================================================
   MAKE STATE FUNCTION AVAILABLE TO HTML ONCLICK
========================================================= */

window.openStateMarketPage =
  openStateMarketPage;



/* =========================================================
   LINK INDIA - LOAD STATE DATA
========================================================= */

async function loadStateMarketData(
  state,
  role = 'farmer'
) {

  console.log(
    'Loading state data:',
    state
  );


  /*
    Each API is loaded independently.

    If markets fail but network works,
    the rest of the page will still work.

    If listings fail, the market page
    will still open.
  */

  const results =
    await Promise.allSettled([


      /* NETWORK */

      api(

        `/api/v2/v3/network?role=${encodeURIComponent(role)}&state=${encodeURIComponent(state)}`

      ),


      /* MARKETS */

      api(

        `/api/markets?state=${encodeURIComponent(state)}`

      ),


      /* PRODUCE LISTINGS */

      api('/api/listings')


    ]);



  /* =====================================================
     NETWORK RESULT
  ===================================================== */

  const network =

    results[0].status === 'fulfilled'

      ? (

          Array.isArray(
            results[0].value
          )

            ? results[0].value

            : []

        )

      : [];



  /* =====================================================
     MARKET RESULT
  ===================================================== */

  const markets =

    results[1].status === 'fulfilled'

      ? (

          Array.isArray(
            results[1].value
          )

            ? results[1].value

            : []

        )

      : [];



  /* =====================================================
     LISTINGS RESULT
  ===================================================== */

  const allListings =

    results[2].status === 'fulfilled'

      ? (

          Array.isArray(
            results[2].value
          )

            ? results[2].value

            : []

        )

      : [];



  /*
    Only listings belonging to the
    currently selected state.
  */

  const listings =

    allListings.filter(

      x =>

        String(
          x.state || ''
        )
          .trim()
          .toLowerCase()

        ===

        String(state)
          .trim()
          .toLowerCase()

    );



  console.log(

    'State data loaded:',

    {

      state: state,

      markets: markets,

      listings: listings,

      network: network

    }

  );



  /* =====================================================
     CALCULATE STATE STATISTICS
  ===================================================== */

  const totalVolume =

    network.reduce(

      (total, x) =>

        total +
        Number(
          x.volume_qtl || 0
        ),

      0

    );



  const verifiedCount =

    network.filter(

      x => x.verified

    ).length;



  /* =====================================================
     UPDATE STATE STAT CARDS
  ===================================================== */

  if ($('stateMarketStats')) {

    $('stateMarketStats').innerHTML = `


      <!-- MARKETS -->

      <div class="india-stat-card">

        <span>
          🏪
        </span>

        <div>

          <small>
            Markets
          </small>

          <b>
            ${markets.length}
          </b>

        </div>

      </div>



      <!-- PRODUCE -->

      <div class="india-stat-card">

        <span>
          🌾
        </span>

        <div>

          <small>
            Produce Listings
          </small>

          <b>
            ${listings.length}
          </b>

        </div>

      </div>



      <!-- VERIFIED NETWORK -->

      <div class="india-stat-card">

        <span>
          👨‍🌾
        </span>

        <div>

          <small>
            Verified Network
          </small>

          <b>
            ${verifiedCount}
          </b>

        </div>

      </div>



      <!-- VOLUME -->

      <div class="india-stat-card">

        <span>
          📦
        </span>

        <div>

          <small>
            Network Volume
          </small>

          <b>

            ${
              totalVolume > 0

                ? `${num(totalVolume)} qtl`

                : '—'
            }

          </b>

        </div>

      </div>


    `;

  }



  /* =====================================================
     RENDER MARKETS

     This function ALREADY EXISTS in your app.js,
     so we are using your existing function.
  ===================================================== */

  if (
    typeof renderStateMarkets
    === 'function'
  ) {

    renderStateMarkets(

      state,

      markets,

      listings,

      role

    );

  }



  /* =====================================================
     RENDER PRODUCE

     This function ALREADY EXISTS in your app.js.
  ===================================================== */

  if (
    typeof renderStateProduce
    === 'function'
  ) {

    renderStateProduce(

      state,

      listings,

      role

    );

  }



  /* =====================================================
     RENDER NETWORK

     This function ALREADY EXISTS in your app.js.
  ===================================================== */

  if (
    typeof renderStateNetwork
    === 'function'
  ) {

    renderStateNetwork(

      state,

      network,

      role

    );

  }



  /* =====================================================
     RENDER MAP

     A map problem must not stop the page.
  ===================================================== */

  if (
    typeof renderStateMap
    === 'function'
  ) {

    try {

      renderStateMap(

        state,

        network

      );

    }

    catch (mapError) {

      console.error(

        'State map error:',

        mapError

      );

    }

  }

}


function renderStateMarkets(
  state,
  markets,
  listings,
  role
) {

  const holder =
    $('stateMarketList');


  if (!holder) return;



  if (!markets.length) {

    holder.innerHTML = `

      <div class="empty">

        No market records are currently available
        for ${esc(state)} in the database.

      </div>

    `;

    return;

  }



  holder.innerHTML =

    markets.map(m => {


      const marketListings =
        listings.filter(

          l =>

            Number(l.market_id) ===
            Number(m.id)

            ||

            String(l.district || '')
              .toLowerCase() ===
            String(m.district || '')
              .toLowerCase()

        );


      const sample =
        marketListings[0] || null;


      const cropNames = [

        ...new Set(

          marketListings

            .map(x => x.crop)

            .filter(Boolean)

        )

      ];


      return `

        <div class="state-market-card">


          <div class="state-market-card-top">


            <div class="market-icon">
              🏪
            </div>


            <div>

              <span class="verified-badge">
                ✓ Market Network
              </span>

              <h3>
                ${esc(m.name)}
              </h3>

              <p>
                📍 ${esc(m.district || state)},
                ${esc(state)}
              </p>

            </div>


          </div>



          <div class="market-information-grid">


            <span>

              Available Crops

              <b>

                ${
                  cropNames.length
                    ? esc(
                        cropNames
                          .slice(0,3)
                          .join(', ')
                      )
                    : 'Check listings'
                }

              </b>

            </span>


            <span>

              Listings

              <b>
                ${marketListings.length}
              </b>

            </span>


            <span>

              Market Type

              <b>
                ${esc(
                  m.type ||
                  m.market_type ||
                  'APMC / Mandi'
                )}
              </b>

            </span>


            <span>

              District

              <b>
                ${esc(m.district || '—')}
              </b>

            </span>


          </div>



          <div class="market-action-row">


            <button
              class="secondary"
              onclick="
                showStateMarketDetails(
                  ${m.id},
                  '${state.replace(/'/g, "\\'")}'
                )
              "
            >
              View Details
            </button>


            ${
              sample

                ? `

                  ${
                    role === 'buyer'

                      ? `

                        <button
                          class="primary"
                          onclick="
                            placeOrder(${sample.id})
                          "
                        >
                          🛒 Buy
                        </button>

                      `

                      : `

                        <button
                          class="primary"
                          onclick="
                            openCrossStateListing(
                              ${sample.id}
                            )
                          "
                        >
                          🌾 View Produce
                        </button>

                      `
                  }


                  <button
                    class="secondary"
                    onclick="
                      openCrossStateNegotiation(
                        ${sample.id},
                        ${Number(
                          sample.seller_id || 0
                        )},
                        ${Number(
                          sample.ask_price || 0
                        )}
                      )
                    "
                  >
                    🤝 Negotiate
                  </button>


                  ${
                    sample.seller_id

                      ? `

                        <button
                          class="secondary"
                          onclick="
                            openBuyerChat(
                              ${sample.seller_id},
                              ${sample.id}
                            )
                          "
                        >
                          💬 Chat
                        </button>

                      `

                      : ''
                  }

                `

                : `

                  <button
                    class="secondary"
                    disabled
                  >
                    No Produce Listed
                  </button>

                `
            }


          </div>


        </div>

      `;

    }).join('');

}
function renderStateProduce(
  state,
  listings,
  role
) {

  const holder =
    $('stateProduceList');


  if (!holder) return;



  if (!listings.length) {

    holder.innerHTML = `

      <div class="empty">

        No verified produce listings are currently
        available in ${esc(state)}.

      </div>

    `;

    return;

  }



  holder.innerHTML =

    listings

      .slice(0, 12)

      .map(l => `


        <div class="india-produce-card">


          ${
            l.certificate && l.certificate.has_photo
              ? `<img class="cert-card-photo" data-cert-photo="${l.certificate.photo_url}" alt="Scanned photo of ${esc(l.crop)}">`
              : ''
          }


          <div class="india-produce-top">


            <span class="produce-icon">
              🌾
            </span>


            <span class="verified-badge">

              ${
                l.quality_verified
                  ? '✓ GRAM Quality Verified'
                  : 'Market Listing'
              }

            </span>


          </div>


          <h3>

            ${esc(l.crop)}

            ${
              l.variety
                ? `• ${esc(l.variety)}`
                : ''
            }

          </h3>


          <p>

            ${esc(
              l.seller_name ||
              'Verified Seller'
            )}

            •

            ${esc(
              l.district ||
              state
            )}

          </p>



          <div class="mini-grid">


            <span>

              Grade

              <b>
                ${esc(l.grade || '—')}
              </b>

            </span>


            <span>

              Quantity

              <b>
                ${num(
                  l.quantity_qtl || 0
                )} qtl
              </b>

            </span>


            <span>

              Price

              <b>
                ${fmt(
                  l.ask_price || 0
                )}/qtl
              </b>

            </span>


            <span>

              Transport

              <b>

                ${
                  l.seller_transport
                    ? 'Available'
                    : 'Self pickup'
                }

              </b>

            </span>


          </div>



          ${certStrip(l.certificate)}


          <div class="market-action-row">


            <button
              class="secondary"
              onclick="
                openCrossStateListing(${l.id})
              "
            >
              View Details
            </button>


            ${
              role === 'buyer'

                ? `

                  <button
                    class="primary"
                    onclick="
                      placeOrder(${l.id})
                    "
                  >
                    Buy
                  </button>

                `

                : ''
            }


            <button
              class="secondary"
              onclick="
                openCrossStateNegotiation(
                  ${l.id},
                  ${Number(l.seller_id || 0)},
                  ${Number(l.ask_price || 0)}
                )
              "
            >
              Negotiate
            </button>


            ${
              l.seller_id

                ? `

                  <button
                    class="secondary"
                    onclick="
                      openBuyerChat(
                        ${l.seller_id},
                        ${l.id}
                      )
                    "
                  >
                    💬 Chat
                  </button>

                `

                : ''
            }


          </div>


        </div>


      `).join('');

}
function renderStateNetwork(
  state,
  rows,
  role
) {

  const holder =
    $('stateNetworkList');


  if (!holder) return;



  if (!rows.length) {

    holder.innerHTML = `

      <div class="empty">

        No network participants currently
        available in ${esc(state)}.

      </div>

    `;

    return;

  }



  holder.innerHTML =

    rows.map(x => `

      <div class="network-card">


        <span class="verified-badge">

          ✓ ${
            x.verified
              ? 'Verified'
              : 'Network'
          }

        </span>


        <h3>
          ${esc(x.name)}
        </h3>


        <p>
          📍 ${esc(x.district)},
          ${esc(x.state)}
        </p>


        <p>
          🌾 ${esc(x.crops || 'Agricultural produce')}
        </p>


        <div class="network-profile-stats">

          <span>

            Rating
            <b>★ ${num(x.rating || 0)}</b>

          </span>


          <span>

            Volume
            <b>${num(x.volume_qtl || 0)} qtl</b>

          </span>

        </div>


        <div class="market-action-row">


          ${
            role === 'farmer'

              ? `

                <button
                  class="primary"
                  onclick="
                    toast(
                      'Use Group Selling to combine produce with this farmer'
                    )
                  "
                >
                  👥 Combine Selling
                </button>

              `

              : ''
          }


          ${
            x.user_id

              ? `

                <button
                  class="secondary"
                  onclick="
                    openBuyerChat(${x.user_id})
                  "
                >
                  💬 Chat
                </button>

              `

              : ''
          }


        </div>


      </div>

    `).join('');

}

function renderStateMap(
  state,
  rows
) {

  if (!$('stateIndiaMap')) return;


  if (mapObj) {

    mapObj.remove();

  }


  let center = [
    22.5,
    79.5
  ];


  if (rows.length) {

    center = [

      Number(rows[0].lat || 22.5),

      Number(rows[0].lon || 79.5)

    ];

  }


  mapObj =
    L.map('stateIndiaMap')
     .setView(
       center,
       rows.length ? 6 : 5
     );


  L.tileLayer(

    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',

    {
      attribution: '© OpenStreetMap'
    }

  ).addTo(mapObj);



  rows.forEach(x => {

    if (
      x.lat === undefined ||
      x.lon === undefined
    ) return;


    L.marker([
      Number(x.lat),
      Number(x.lon)
    ])

    .addTo(mapObj)

    .bindPopup(`

      <b>${esc(x.name)}</b>

      <br>

      ${esc(x.district)},
      ${esc(state)}

      <br>

      ${esc(x.crops || '')}

      <br>

      ★ ${num(x.rating || 0)}

    `);

  });

}

async function showStateMarketDetails(
  marketId,
  state
) {

  try {

    const markets =
      await api(
        `/api/markets?state=${encodeURIComponent(state)}`
      );


    const market =
      markets.find(
        x =>
          Number(x.id) ===
          Number(marketId)
      );


    if (!market) {

      throw new Error(
        'Market details not found'
      );

    }


    $('modalBody').innerHTML = `

      <div class="state-market-modal">


        <span class="verified-badge">
          ✓ GRAM Market Network
        </span>


        <h2>
          ${esc(market.name)}
        </h2>


        <p>
          📍 ${esc(market.district || state)},
          ${esc(state)}
        </p>


        <div class="mini-grid">


          <span>

            State

            <b>
              ${esc(state)}
            </b>

          </span>


          <span>

            District

            <b>
              ${esc(
                market.district ||
                '—'
              )}
            </b>

          </span>


          <span>

            Market Type

            <b>
              ${esc(
                market.market_type ||
                market.type ||
                'APMC / Mandi'
              )}
            </b>

          </span>


          <span>

            Market ID

            <b>
              #${market.id}
            </b>

          </span>


        </div>


        <div class="security-note">

          Prices, listings and sellers shown in Link India
          are obtained from the market/network data
          currently available in GRAM AI.

        </div>


      </div>

    `;


    $('modal')
      .classList
      .remove('hidden');


  }

  catch (e) {

    toast(e.message);

  }

}

async function openCrossStateListing(id) {

  try {

    const d =
      await api(
        `/api/v2/v3/listings/${id}`
      );


    $('modalBody').innerHTML = `

      <div class="cross-state-listing-modal">


        <span class="verified-badge">

          ${
            d.gram_verified
              ? '✓ GRAM AI Verified'
              : 'Market Listing'
          }

        </span>


        <h2>
          ${esc(d.crop)}
          •
          ${esc(d.variety || '')}
        </h2>


        <p>
          ${esc(
            d.farmer_name ||
            d.seller_name ||
            'Seller'
          )}
          •
          ${esc(d.district || '')},
          ${esc(d.state || '')}
        </p>



        <div class="quality-result">

          <div>

            <small>
              Quality Grade
            </small>

            <b>
              Grade ${esc(d.grade || '—')}
            </b>

            <span>

              ${
                d.quality_confidence
                  ? `${num(
                      Number(d.quality_confidence) <= 1
                        ? Number(d.quality_confidence) * 100
                        : Number(d.quality_confidence)
                    )}% confidence`
                  : ''
              }

            </span>

          </div>

        </div>



        <div class="mini-grid">


          <span>

            Quantity

            <b>
              ${num(
                d.quantity_qtl || 0
              )} qtl
            </b>

          </span>


          <span>

            Ask Price

            <b>
              ${fmt(
                d.ask_price || 0
              )}/qtl
            </b>

          </span>


          <span>

            Transport

            <b>

              ${
                d.seller_transport
                  ? 'Available'
                  : 'Self pickup'
              }

            </b>

          </span>


          <span>

            ₹ / km

            <b>

              ${
                d.transport_cost_per_km
                  ? `${fmt(
                      d.transport_cost_per_km
                    )}/km`
                  : '—'
              }

            </b>

          </span>


        </div>



        <div class="action-row">


          ${
            d.certificate_url

              ? `

                <button
                  class="secondary"
                  onclick="
                    openCertificate(
                      '${d.certificate_url}'
                    )
                  "
                >
                  📄 Certificate
                </button>

              `

              : ''
          }


          ${
            d.seller_id

              ? `

                <button
                  class="secondary"
                  onclick="
                    openBuyerChat(
                      ${d.seller_id},
                      ${d.id}
                    );
                    closeModal();
                  "
                >
                  💬 Chat
                </button>

              `

              : ''
          }


        </div>


      </div>

    `;


    $('modal')
      .classList
      .remove('hidden');


  }

  catch (e) {

    toast(e.message);

  }

}

async function openCrossStateNegotiation(
  listingId,
  sellerId,
  askPrice
) {

  try {

    if (!sellerId) {

      throw new Error(
        'Seller chat account is unavailable'
      );

    }


    await ensureChatWithBuyer(
      sellerId,
      listingId,
      null,
      `I would like to discuss your listing. Current listed price is ${fmt(askPrice)}/qtl.`
    );


    localStorage.setItem(
      'gram_open_chat_user',
      String(sellerId)
    );


    localStorage.setItem(
      'gram_open_chat_listing',
      String(listingId)
    );


    localStorage.setItem(
      'gram_negotiation_offer',
      `LINK_INDIA_${listingId}`
    );


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}



async function chatsPage() {

  try {

    const threads =
      await api('/api/v2/v3/chats');


    $('content').innerHTML = `

      <div class="gram-chat-page">


        <div class="gram-thread-sidebar">


          <div class="chat-sidebar-head">

            <div>

              <h2>
                💬 Chats
              </h2>

              <small>
                Buyer conversations
              </small>

            </div>

          </div>


          <div class="chat-thread-list">

            ${

              threads.length

                ? threads.map(t => {

                    const otherId =
                      Number(t.farmer_id) === Number(me.id)
                        ? t.buyer_id
                        : t.farmer_id;


                    const otherName =
                      me.role === 'farmer'
                        ? t.buyer_name
                        : t.farmer_name;


                    const initial =
                      String(
                        otherName || 'U'
                      )
                        .charAt(0)
                        .toUpperCase();


                    return `

                      <button

                        class="chat-thread-button"

                        id="chatThreadBtn-${t.id}"

                        onclick="
                          selectChatThread(
                            ${t.id},
                            ${otherId},
                            '${esc(
                              String(otherName || 'User')
                            )}'
                          )
                        "
                      >


                        <div class="thread-avatar">

                          ${esc(initial)}

                        </div>


                        <div class="thread-info">

                          <b>
                            ${esc(otherName)}
                          </b>

                          <small>

                            ${esc(
                              t.last_message ||
                              'Start conversation'
                            )}

                          </small>

                        </div>


                        <span class="thread-count">

                          ${
                            Number(
                              t.message_count || 0
                            )
                          }

                        </span>


                      </button>

                    `;

                  }).join('')

                : `

                    <div class="empty">

                      No conversations yet.

                      Start a chat from Market & Offers.

                    </div>

                  `

            }

          </div>


        </div>



        <div
          id="threadPane"
          class="gram-conversation-pane"
        >

          <div class="chat-empty-state">

            <div>
              💬
            </div>

            <h3>
              Your Messages
            </h3>

            <p>
              Select a buyer to start chatting.
            </p>

          </div>

        </div>


      </div>

    `;



    const wantedUser =
      Number(
        localStorage.getItem(
          'gram_open_chat_user'
        ) || 0
      );


    const wantedThread =
      Number(
        localStorage.getItem(
          'gram_open_thread'
        ) || 0
      );



    let selected = null;


    if (wantedThread) {

      selected =
        threads.find(
          t =>
            Number(t.id) ===
            wantedThread
        );

    }



    if (!selected && wantedUser) {

      selected =
        threads.find(

          t => {

            const otherId =
              Number(t.farmer_id) === Number(me.id)
                ? Number(t.buyer_id)
                : Number(t.farmer_id);


            return (
              otherId === wantedUser
            );

          }

        );

    }



    if (!selected && threads.length === 1) {

      selected = threads[0];

    }



    if (selected) {

      const otherId =
        Number(selected.farmer_id) === Number(me.id)
          ? selected.buyer_id
          : selected.farmer_id;


      const otherName =
        me.role === 'farmer'
          ? selected.buyer_name
          : selected.farmer_name;


      await selectChatThread(
        selected.id,
        otherId,
        otherName
      );

    }


  }

  catch (e) {

    toast(e.message);

  }

}
async function selectChatThread(
  threadId,
  otherUserId,
  otherName
) {

  try {


    document
      .querySelectorAll(
        '.chat-thread-button'
      )
      .forEach(
        b =>
          b.classList.remove(
            'active'
          )
      );


    const activeButton =
      $(
        `chatThreadBtn-${threadId}`
      );


    if (activeButton) {

      activeButton
        .classList
        .add('active');

    }


    localStorage.setItem(
      'gram_open_thread',
      String(threadId)
    );


    localStorage.setItem(
      'gram_open_chat_user',
      String(otherUserId)
    );


    const messages =
      await api(
        `/api/v2/v3/chats/${threadId}`
      );


    const isNegotiation =
      Boolean(
        localStorage.getItem(
          'gram_negotiation_offer'
        )
      );


    $('threadPane').innerHTML = `


      <div class="conversation-header">


        <div class="thread-avatar large">

          ${esc(
            String(
              otherName || 'U'
            )
              .charAt(0)
              .toUpperCase()
          )}

        </div>


        <div>

          <h3>
            ${esc(otherName || 'Buyer')}
          </h3>

          <small>

            ${
              isNegotiation
                ? 'Price negotiation'
                : 'Buyer conversation'
            }

          </small>

        </div>


        <span class="verified-badge">

          ✓ GRAM Verified

        </span>


      </div>



      ${

        isNegotiation

          ? `

            <div class="negotiation-banner">

              <div>

                <b>
                  🤝 Negotiation Mode
                </b>

                <small>
                  Use a quick message or type your own offer.
                </small>

              </div>

            </div>


            <div class="quick-message-wrap">


              <button
                onclick="useQuickMessage(
                  'Can you increase your offer slightly?'
                )"
              >
                Can you increase your offer slightly?
              </button>


              <button
                onclick="useQuickMessage(
                  'I can accept if you pay the token immediately.'
                )"
              >
                I can accept with immediate token payment.
              </button>


              <button
                onclick="useQuickMessage(
                  'Can we split the transport cost?'
                )"
              >
                Can we split transport cost?
              </button>


              <button
                onclick="useQuickMessage(
                  'I can offer this quantity at a slightly higher price.'
                )"
              >
                I need a slightly higher price.
              </button>


              <button
                onclick="useQuickMessage(
                  'If you increase the quantity, I can discuss a better price.'
                )"
              >
                Increase quantity for better price.
              </button>


            </div>

          `

          : ''

      }



      <div
        id="chatMessageArea"
        class="instagram-message-area"
      >


        ${

          messages.length

            ? messages.map(m => {

                const mine =
                  Number(m.sender_id) ===
                  Number(me.id);


                return `

                  <div class="
                    message-row
                    ${mine ? 'mine' : 'theirs'}
                  ">


                    ${
                      !mine

                        ? `

                          <div class="message-mini-avatar">

                            ${esc(
                              String(
                                m.sender_name ||
                                otherName ||
                                'U'
                              )
                                .charAt(0)
                                .toUpperCase()
                            )}

                          </div>

                        `

                        : ''

                    }


                    <div class="message-bubble">


                      <p>

                        ${esc(m.message)}

                      </p>


                      ${
                        m.offer_price

                          ? `

                            <div class="message-offer">

                              Offer:
                              ${fmt(m.offer_price)}/qtl

                            </div>

                          `

                          : ''
                      }


                      <small>

                        ${mine ? 'You' : esc(m.sender_name)}

                      </small>


                    </div>


                  </div>

                `;

              }).join('')

            : `

                <div class="chat-empty-conversation">

                  Start your conversation with
                  ${esc(otherName || 'the buyer')}.

                </div>

              `

        }


      </div>



      <div class="instagram-compose">


        <button
          class="chat-tool-btn"
          onclick="voiceInto('threadInput')"
          title="Voice message"
        >

          🎙

        </button>


        <input
          id="threadInput"
          class="chat-message-input"
          placeholder="Message ${esc(otherName || 'buyer')}..."
          onkeydown="
            if(event.key === 'Enter'){
              sendInstagramMessage(
                ${otherUserId},
                ${threadId}
              )
            }
          "
        >


        <button
          class="chat-send-btn"
          onclick="
            sendInstagramMessage(
              ${otherUserId},
              ${threadId}
            )
          "
        >

          Send

        </button>


      </div>

    `;


    setTimeout(

      () => {

        const area =
          $('chatMessageArea');

        if (area) {

          area.scrollTop =
            area.scrollHeight;

        }

      },

      30

    );


  }

  catch (e) {

    toast(e.message);

  }

}

function useQuickMessage(text) {

  const input =
    $('threadInput');


  if (!input) return;


  input.value =
    text;


  input.focus();

}
async function sendInstagramMessage(
  otherUserId,
  threadId
) {

  try {


    const input =
      $('threadInput');


    const message =
      input?.value.trim();


    if (!message) {

      return;

    }


    input.value = '';


    const threads =
      await api('/api/v2/v3/chats');


    const thread =
      threads.find(
        x =>
          Number(x.id) ===
          Number(threadId)
      );


    await api(

      '/api/v2/v3/chats',

      {

        method: 'POST',

        body: JSON.stringify({

          other_user_id:
            Number(otherUserId),

          message:
            message,

          listing_id:
            thread?.listing_id || null,

          preorder_id:
            thread?.preorder_id || null

        })

      }

    );


    const otherName =
      me.role === 'farmer'
        ? thread?.buyer_name
        : thread?.farmer_name;


    await selectChatThread(

      threadId,

      otherUserId,

      otherName || 'Buyer'

    );


  }

  catch (e) {

    toast(e.message);

  }

}


async function replyThread(other,thread){let text=$('threadInput').value;if(!text)return;let ts=await api('/api/v2/v3/chats'),t=ts.find(x=>x.id===thread);await api('/api/v2/v3/chats',{method:'POST',body:JSON.stringify({other_user_id:other,message:text,listing_id:t.listing_id,preorder_id:t.preorder_id})});openThread(thread,other)}

// BUYER
async function buyerRoute(k){if(k==='dashboard')return buyerDashboard();if(k==='discover')return buyerDiscover();if(k==='preorders')return buyerPreorders();if(k==='orders')return buyerOrders();if(k==='bulk')return buyerBulk();if(k==='rewards')return paymentsRewardsPage();if(k==='profile')return profilePage();if(k==='feedback')return buyerFeedbackPage();if(k==='grievances')return buyerGrievancePage();if(k==='connectBuyers')return networkPage('buyer');if(k==='chats')return chatsPage()}
async function buyerDashboard(){let [d,orders,notes]=await Promise.all([api('/api/v2/v3/dashboard'),api('/api/orders'),api('/api/notifications')]);$('content').innerHTML=`<div class="hero-reco"><div><small>${tr('todayRecommendation')}</small><h2>${esc(d.recommendation)}</h2><p>Area: ${esc(d.district)}, Tamil Nadu</p></div>${badge(d.kyc.status==='VERIFIED'&&d.kyc.live_check)}</div><div class="grid stats-4">${card(tr('purchased'),d.orders,'Orders placed')}${card('Purchase Value',fmt(d.spend),'Recorded order value')}${card(tr('preorders'),d.preorders,'Harvest commitments')}${card(tr('rewardPoints'),d.reward_points,'Buyer rewards')}</div>${section(tr('tracking'),orders.slice(0,5).map(o=>`<div class="list-item"><div><b>Order #${o.id} • ${esc(o.crop)}</b><small>${esc(o.district)}, Tamil Nadu • ${esc(o.status)}</small></div><button class="secondary" onclick="showTracking(${o.id})">Track</button></div>`).join('')||'<div class="empty">No orders yet.</div>')}${section(tr('notification'),notes.slice(0,5).map(n=>`<div class="list-item"><div><b>${esc(n.title)}</b><small>${esc(n.message)}</small></div></div>`).join(''))}`}

async function buyerDiscover() {

  try {

    let listings =
      await api('/api/listings');


    listings =
      Array.isArray(listings)
        ? listings.filter(
            x =>
              String(x.state || '').toLowerCase()
              === 'tamil nadu'
          )
        : [];


    $('content').innerHTML = `

      <div class="buyer-discover-page">


        <div class="discover-hero">

          <div>

            <span class="verified-badge">
              ✓ GRAM AI Verified Marketplace
            </span>

            <h2>
              Discover Verified Harvests
            </h2>

            <p>
              Compare verified produce,
              farmer price, quality grade,
              transport availability and
              secure purchasing details.
            </p>

          </div>

        </div>


        ${
          section(

            tr('availableHarvests'),

            listings.length

            ? `

              <div class="discover-grid">

                ${

                  listings.map(l => `


                    <div class="listing-card">


                      <!-- PRODUCE PHOTO -->

                      <div class="listing-photo">

                        ${
                          l.quality_image || l.image_url

                          ? `

                            <img
                              src="${
                                l.certificate && l.certificate.has_photo
                                  ? ''
                                  : esc(l.quality_image || l.image_url)
                              }"
                              data-cert-photo="${
                                l.certificate && l.certificate.has_photo
                                  ? l.certificate.photo_url
                                  : ''
                              }"
                              alt="${esc(l.crop)}"
                              class="discover-produce-image"
                              onerror="
                                this.style.display='none';
                                this.nextElementSibling.style.display='flex';
                              "
                            >

                            <div
                              class="photo-placeholder"
                              style="display:none"
                            >
                              🌾
                            </div>

                          `

                          : `

                            <div class="photo-placeholder">
                              🌾
                            </div>

                          `
                        }

                      </div>


                      <!-- LISTING BODY -->

                      <div class="listing-body">


                        <div>

                          ${
                            l.quality_verified

                            ? `
                              <span class="verified-badge">
                                ✓ GRAM Quality Verified
                              </span>
                            `

                            : `
                              <span class="tag">
                                Quality Verification Pending
                              </span>
                            `
                          }

                        </div>


                        <!-- QUALITY CERTIFICATE: scan date + validity -->

                        ${certStrip(l.certificate)}


                        <h3>

                          ${esc(l.crop)}
                          •
                          Grade ${esc(l.grade || '—')}

                        </h3>


                        <p>

                          ${esc(
                            l.seller_name
                            || 'Verified Farmer'
                          )}

                          •

                          ${esc(l.district || '')},
                          Tamil Nadu

                        </p>


                        <div class="mini-grid">


                          <span>

                            ${tr('quantity')}

                            <b>
                              ${num(l.quantity_qtl)} qtl
                            </b>

                          </span>


                          <span>

                            ${tr('price')}

                            <b>
                              ${fmt(l.ask_price)}/qtl
                            </b>

                          </span>


                          <span>

                            Transport

                            <b>

                              ${
                                l.seller_transport
                                  ? 'Seller Available'
                                  : 'Buyer Pickup'
                              }

                            </b>

                          </span>


                          <span>

                            Transport Rate

                            <b>

                              ${
                                l.seller_transport

                                ? `${fmt(
                                    l.transport_cost_per_km
                                  )}/km`

                                : '—'
                              }

                            </b>

                          </span>


                        </div>


                        <div class="action-row">


                          <button
                            class="primary"
                            onclick="viewListing(${l.id})"
                          >
                            👁 ${tr('viewDetails')}
                          </button>


                          <button
                            class="secondary"
                            onclick="
                              openBuyerListingNegotiation(
                                ${l.id},
                                ${l.seller_id},
                                ${Number(l.ask_price || 0)}
                              )
                            "
                          >
                            🤝 ${tr('negotiate')}
                          </button>


                          <button
                            class="secondary"
                            onclick="
                              openSellerChatFromListing(
                                ${l.seller_id},
                                ${l.id}
                              )
                            "
                          >
                            💬 ${tr('chat')}
                          </button>


                        </div>


                      </div>


                    </div>


                  `).join('')

                }

              </div>

            `

            : `

              <div class="empty">

                No verified harvests are
                currently available in Tamil Nadu.

              </div>

            `

          )
        }


      </div>

    `;


  }

  catch (e) {

    $('content').innerHTML = `

      <div class="card error">
        ${esc(e.message)}
      </div>

    `;

  }

}

async function viewListing(id) {

  try {

    const d =
      await api(
        `/api/v2/v3/listings/${id}`
      );


    let quote = {};

    try {

      quote =
        await api(

          `/api/listings/${id}/quote?quantity_qtl=1&buyer_lat=19.076&buyer_lon=72.8777`

        );

    }

    catch {

      quote = {};

    }


    const imageUrl =
      d.quality_image
      || d.image_url
      || '';


    $('modalBody').innerHTML = `

      <div class="buyer-listing-detail">


        <!-- HEADER -->

        <div class="listing-detail-head">

          <div>

            <span class="verified-badge">
              ✓ GRAM Marketplace Listing
            </span>

            <h2>
              ${esc(d.crop)}
              •
              ${esc(d.variety || 'Standard')}
            </h2>

            <p>
              Review all harvest details
              before placing an order.
            </p>

          </div>

        </div>



        <!-- PRODUCE PHOTO -->

        <div class="order-produce-photo">

          ${
            imageUrl

            ? `

              <img
                src="${esc(imageUrl)}"
                alt="${esc(d.crop)} produce"
                class="order-detail-image"
                onerror="
                  this.style.display='none';
                  this.nextElementSibling.style.display='flex';
                "
              >

              <div
                class="photo-placeholder large-photo-placeholder"
                style="display:none"
              >
                🌾 Produce image unavailable
              </div>

            `

            : `

              <div class="photo-placeholder large-photo-placeholder">
                🌾 Produce image unavailable
              </div>

            `
          }

        </div>



        <!-- QUALITY -->

        <div class="quality-result">

          <div>

            <small>
              ${tr('qualityGrade')}
            </small>

            <b>
              Grade ${esc(d.grade || '—')}
            </b>

            <span>

              ${
                d.quality_confidence != null

                ? `${num(
                    Number(d.quality_confidence) <= 1
                      ? Number(d.quality_confidence) * 100
                      : Number(d.quality_confidence)
                  )}% confidence`

                : 'GRAM AI quality record'
              }

            </span>

          </div>


          <div>

            ${
              d.gram_verified

              ? `
                <span class="verified-badge">
                  ✓ GRAM AI Verified
                </span>
              `

              : `
                <span class="tag">
                  Verification Pending
                </span>
              `
            }

          </div>

        </div>



        <!-- DETAILS -->

        <div class="mini-grid">


          <span>

            Farmer

            <b>
              ${esc(
                d.farmer_name
                || d.seller_name
                || 'Farmer'
              )}
            </b>

          </span>


          <span>

            ${tr('location')}

            <b>

              ${esc(d.district || '')},
              ${esc(d.state || 'Tamil Nadu')}

            </b>

          </span>


          <span>

            Crop

            <b>
              ${esc(d.crop)}
            </b>

          </span>


          <span>

            Variety

            <b>
              ${esc(d.variety || 'Standard')}
            </b>

          </span>


          <span>

            Grade

            <b>
              ${esc(d.grade || '—')}
            </b>

          </span>


          <span>

            Available Quantity

            <b>
              ${num(d.quantity_qtl)} qtl
            </b>

          </span>


          <span>

            Farmer Ask Price

            <b>
              ${fmt(d.ask_price)}/qtl
            </b>

          </span>


          <span>

            Harvest Date

            <b>
              ${esc(
                d.harvest_date
                || d.expected_harvest_date
                || 'Available now'
              )}
            </b>

          </span>


          <span>

            Packaging

            <b>
              ${esc(
                d.packaging
                || 'Standard packaging'
              )}
            </b>

          </span>


          <span>

            Minimum Order

            <b>
              ${num(
                d.min_order_qtl || 1
              )} qtl
            </b>

          </span>


          <span>

            Seller Transport

            <b>

              ${
                d.seller_transport
                  ? 'Available'
                  : 'Not Available'
              }

            </b>

          </span>


          <span>

            Transport ₹ / km

            <b>

              ${
                d.seller_transport

                ? `${fmt(
                    d.transport_cost_per_km
                    || 0
                  )}/km`

                : '—'
              }

            </b>

          </span>


          <span>

            Delivery Radius

            <b>
              ${num(
                d.delivery_radius_km || 0
              )} km
            </b>

          </span>


          <span>

            Estimated Distance

            <b>

              ${
                quote.estimated_distance_km != null

                ? `${num(
                    quote.estimated_distance_km
                  )} km`

                : 'Calculated at checkout'
              }

            </b>

          </span>


          <span>

            Estimated Transport

            <b>

              ${
                quote.estimated_transport_cost != null

                ? fmt(
                    quote.estimated_transport_cost
                  )

                : 'Calculated at checkout'
              }

            </b>

          </span>


        </div>



        <!-- NOTES -->

        ${
          d.quality_notes

          ? `

            <div class="info-panel">

              <b>
                🌾 Produce Notes
              </b>

              <p>
                ${esc(d.quality_notes)}
              </p>

            </div>

          `

          : ''
        }



        <!-- ACTIONS -->

        <div class="action-row">


          ${
            d.certificate_url

            ? `

              <button
                class="secondary"
                onclick="
                  openCertificate(
                    '${d.certificate_url}'
                  )
                "
              >
                📄 ${tr('certificate')}
              </button>

            `

            : ''
          }


          <button
            class="primary"
            onclick="
              openOrderConfirmation(${id})
            "
          >
            🛒 ${tr('placeOrder')}
          </button>


          <button
            class="secondary"
            onclick="
              openBuyerListingNegotiation(
                ${id},
                ${d.seller_id},
                ${Number(d.ask_price || 0)}
              )
            "
          >
            🤝 ${tr('negotiate')}
          </button>


          <button
            class="secondary"
            onclick="
              openSellerChatFromListing(
                ${d.seller_id},
                ${id}
              )
            "
          >
            💬 ${tr('chat')}
          </button>


        </div>


      </div>

    `;


    $('modal').classList.remove(
      'hidden'
    );


  }

  catch (e) {

    toast(e.message);

  }

}
async function openSellerChatFromListing(
  sellerId,
  listingId
) {

  try {

    if (!sellerId) {

      throw new Error(
        'Farmer chat account unavailable'
      );

    }


    await ensureChatWithBuyer(

      sellerId,

      listingId,

      null,

      null

    );


    localStorage.setItem(

      'gram_open_chat_user',

      String(sellerId)

    );


    localStorage.setItem(

      'gram_open_chat_listing',

      String(listingId || '')

    );


    localStorage.removeItem(
      'gram_negotiation_offer'
    );


    closeModal();


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}
async function openBuyerListingNegotiation(
  listingId,
  sellerId,
  askPrice
) {

  try {

    if (!sellerId) {

      throw new Error(
        'Farmer account unavailable'
      );

    }


    /*
      Create / locate listing chat.
    */

    await ensureChatWithBuyer(

      sellerId,

      listingId,

      null,

      `I would like to negotiate the price for this harvest.`

    );


    /*
      Open this exact seller in Chats.
    */

    localStorage.setItem(

      'gram_open_chat_user',

      String(sellerId)

    );


    localStorage.setItem(

      'gram_open_chat_listing',

      String(listingId)

    );


    /*
      This tells chatsPage that
      negotiation mode should be shown.
    */

    localStorage.setItem(

      'gram_negotiation_offer',

      `BUYER_LISTING_${listingId}`

    );


    localStorage.setItem(

      'gram_negotiation_ask_price',

      String(
        Number(askPrice || 0)
      )

    );


    closeModal();


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}

async function openOrderConfirmation(id) {

  try {

    const d =
      await api(
        `/api/v2/v3/listings/${id}`
      );


    closeModal();


    $('content').innerHTML = `

      <div class="buyer-order-confirmation">


        <div class="confirmation-page-head">


          <button
            class="secondary"
            onclick="buyerDiscover()"
          >
            ← Back to Harvest
          </button>


          <div>

            <span class="verified-badge">
              🔒 Secure GRAM AI Order
            </span>

            <h2>
              Confirm Your Order
            </h2>

            <p>
              Check the farmer, produce,
              quantity, transport and payable
              estimate before placing the order.
            </p>

          </div>


        </div>



        <div class="order-confirm-grid">


          <!-- LEFT -->

          <div class="card">


            <h3>
              🌾 Harvest Details
            </h3>


            <div class="order-produce-photo">

              ${
                d.quality_image || d.image_url

                ? `

                  <img
                    src="${esc(
                      d.quality_image
                      || d.image_url
                    )}"
                    class="order-detail-image"
                    alt="${esc(d.crop)}"
                    onerror="
                      this.style.display='none';
                      this.nextElementSibling.style.display='flex';
                    "
                  >

                  <div
                    class="photo-placeholder large-photo-placeholder"
                    style="display:none"
                  >
                    🌾
                  </div>

                `

                : `

                  <div class="photo-placeholder large-photo-placeholder">
                    🌾
                  </div>

                `
              }

            </div>


            <div class="mini-grid">


              <span>

                Crop

                <b>
                  ${esc(d.crop)}
                </b>

              </span>


              <span>

                Variety

                <b>
                  ${esc(
                    d.variety || 'Standard'
                  )}
                </b>

              </span>


              <span>

                Grade

                <b>
                  ${esc(d.grade || '—')}
                </b>

              </span>


              <span>

                Available

                <b>
                  ${num(d.quantity_qtl)} qtl
                </b>

              </span>


              <span>

                Ask Price

                <b>
                  ${fmt(d.ask_price)}/qtl
                </b>

              </span>


              <span>

                Farmer

                <b>
                  ${esc(
                    d.farmer_name
                    || d.seller_name
                    || 'Farmer'
                  )}
                </b>

              </span>


              <span>

                Location

                <b>

                  ${esc(
                    d.district || ''
                  )},

                  ${esc(
                    d.state || 'Tamil Nadu'
                  )}

                </b>

              </span>


              <span>

                Packaging

                <b>
                  ${esc(
                    d.packaging
                    || 'Standard'
                  )}
                </b>

              </span>


            </div>


          </div>



          <!-- RIGHT -->

          <div class="card">


            <h3>
              🛒 Order Details
            </h3>


            <div class="field">

              <label>
                Quantity Required (qtl)
              </label>

              <input
                id="buyerOrderQty"
                class="control"
                type="number"
                value="${
                  Math.min(
                    2,
                    Number(
                      d.quantity_qtl || 1
                    )
                  )
                }"
                min="${
                  Number(
                    d.min_order_qtl || 1
                  )
                }"
                max="${
                  Number(
                    d.quantity_qtl || 1
                  )
                }"
                oninput="
                  updateBuyerOrderSummary(${id})
                "
              >

            </div>



            <div class="field">

              <label>
                Delivery Method
              </label>

              <select
                id="buyerDeliveryMode"
                class="control"
                onchange="
                  updateBuyerOrderSummary(${id})
                "
              >

                ${
                  d.seller_transport

                  ? `

                    <option value="SELLER_TRANSPORT">
                      Seller Transport
                    </option>

                  `

                  : ''
                }

                <option value="BUYER_PICKUP">
                  Buyer Pickup
                </option>

              </select>

            </div>



            ${
              d.seller_transport

              ? `

                <div class="info-panel">

                  🚚 Seller transport available at

                  <b>
                    ${fmt(
                      d.transport_cost_per_km
                      || 0
                    )}/km
                  </b>

                  up to

                  <b>
                    ${num(
                      d.delivery_radius_km
                      || 0
                    )} km
                  </b>.

                </div>

              `

              : `

                <div class="info-panel">

                  🚚 Seller transport is not
                  available for this listing.
                  Buyer pickup is required.

                </div>

              `
            }



            <div
              id="buyerOrderSummary"
            >

              <div class="ai-processing">
                Calculating secure order total...
              </div>

            </div>


          </div>


        </div>


        <div class="action-row">


          <button
            class="secondary"
            onclick="buyerDiscover()"
          >
            Cancel
          </button>


          <button
            class="primary"
            onclick="
              confirmBuyerOrder(${id})
            "
          >
            ✓ Confirm & Place Order
          </button>


        </div>


      </div>

    `;


    setTimeout(

      () =>
        updateBuyerOrderSummary(id),

      40

    );


  }

  catch (e) {

    toast(e.message);

  }

}
async function updateBuyerOrderSummary(id) {

  const holder =
    $('buyerOrderSummary');


  if (!holder) return;


  try {

    const qty =
      Number(
        $('buyerOrderQty')?.value || 0
      );


    if (qty <= 0) {

      holder.innerHTML = `

        <div class="danger-tag">
          Enter a valid quantity.
        </div>

      `;

      return;

    }


    holder.innerHTML = `

      <div class="ai-processing">
        Calculating secure order total...
      </div>

    `;


    const quote =
      await api(

        `/api/listings/${id}/quote?quantity_qtl=${encodeURIComponent(qty)}&buyer_lat=19.076&buyer_lon=72.8777`

      );


    localStorage.setItem(

      'gram_buyer_order_quote',

      JSON.stringify(quote)

    );


    holder.innerHTML = `

      <div class="order-price-summary">


        <h3>
          Payment Estimate
        </h3>


        <div class="summary-line">

          <span>
            Produce Value
          </span>

          <b>
            ${fmt(
              quote.produce_total
              || quote.produce_value
              || 0
            )}
          </b>

        </div>


        <div class="summary-line">

          <span>
            Estimated Transport
          </span>

          <b>
            ${fmt(
              quote.estimated_transport_cost
              || quote.transport_total
              || 0
            )}
          </b>

        </div>


        ${
          quote.platform_fee != null

          ? `

            <div class="summary-line">

              <span>
                Platform Fee
              </span>

              <b>
                ${fmt(
                  quote.platform_fee
                )}
              </b>

            </div>

          `

          : ''
        }


        <div class="summary-line total-line">

          <span>
            Estimated Total
          </span>

          <b>

            ${fmt(

              quote.total

              ||

              (
                Number(
                  quote.produce_total
                  || quote.produce_value
                  || 0
                )

                +

                Number(
                  quote.estimated_transport_cost
                  || quote.transport_total
                  || 0
                )

                +

                Number(
                  quote.platform_fee
                  || 0
                )
              )

            )}

          </b>

        </div>


        ${
          quote.estimated_distance_km != null

          ? `

            <small>

              Estimated distance:
              ${num(
                quote.estimated_distance_km
              )} km

            </small>

          `

          : ''
        }


      </div>

    `;


  }

  catch (e) {

    holder.innerHTML = `

      <div class="info-panel">

        Final payable amount will be
        calculated securely by GRAM AI
        when the order is placed.

      </div>

    `;

  }

}

async function confirmBuyerOrder(id) {

  try {

    const qty =
      Number(
        $('buyerOrderQty')?.value || 0
      );


    const deliveryMode =
      $('buyerDeliveryMode')?.value
      || 'BUYER_PICKUP';


    if (!qty || qty <= 0) {

      throw new Error(
        'Enter a valid order quantity'
      );

    }


    const btn =
      event?.target;


    if (btn) {

      btn.disabled = true;

      btn.textContent =
        'Placing Secure Order...';

    }


    /*
      IMPORTANT:
      Backend calculates authoritative
      amount. Frontend does not send total.
    */

    const result =
      await api(

        '/api/orders',

        {

          method: 'POST',

          body: JSON.stringify({

            listing_id:
              Number(id),

            quantity_qtl:
              qty,

            delivery_mode:
              deliveryMode,

            buyer_lat:
              19.076,

            buyer_lon:
              72.8777

          })

        }

      );


    const orderId =
      result.order_id
      || result.id;


    showBuyerOrderSuccess(
      orderId,
      result
    );


  }

  catch (e) {

    toast(e.message);


    try {

      if (event?.target) {

        event.target.disabled = false;

        event.target.textContent =
          '✓ Confirm & Place Order';

      }

    }

    catch {}

  }

}

function showBuyerOrderSuccess(
  orderId,
  result = {}
) {

  $('content').innerHTML = `

    <div class="order-success-page">


      <div class="order-success-card">


        <div class="success-tick">
          ✓
        </div>


        <span class="verified-badge">
          Order Created Successfully
        </span>


        <h1>
          Your Order is Confirmed
        </h1>


        <p>

          GRAM AI has recorded your
          purchase request securely.

        </p>


        <div class="success-order-number">

          Order #

          <b>
            ${esc(orderId || '—')}
          </b>

        </div>


        ${
          result.total != null

          ? `

            <div class="success-total">

              Order Total

              <b>
                ${fmt(result.total)}
              </b>

            </div>

          `

          : ''
        }


        <div class="info-panel">

          📍 You can now track the order
          from confirmation through pickup,
          transport and delivery.

        </div>


        <div class="action-row">


          <button
            class="primary"
            onclick="
              openConfirmedOrderTracking(
                ${Number(orderId || 0)}
              )
            "
          >
            📍 Track Order
          </button>


          <button
            class="secondary"
            onclick="
              buyerOrders()
            "
          >
            📦 My Orders
          </button>


          <button
            class="secondary"
            onclick="
              buyerDiscover()
            "
          >
            Continue Shopping
          </button>


        </div>


      </div>


    </div>

  `;

}
async function openConfirmedOrderTracking(
  orderId
) {

  if (!orderId) {

    toast(
      'Order number unavailable'
    );

    return;

  }


  try {

    await showTracking(
      orderId
    );

  }

  catch (e) {

    toast(e.message);

  }

}



function buyerOffer(id,ask){let price=prompt('Your offer ₹/qtl',Math.round(ask*.98)),qty=prompt('Quantity qtl','5'),pitch=prompt('Pitch to farmer','I can pay token immediately and arrange quick pickup.');if(!price||!qty)return;api('/api/v2/v3/offers',{method:'POST',body:JSON.stringify({listing_id:id,offer_price:+price,quantity_qtl:+qty,pitch})}).then(()=>toast('Offer sent to farmer')).catch(e=>toast(e.message))}
async function placeOrder(id){let qty=prompt('Quantity qtl','2');if(!qty)return;try{let d=await api('/api/orders',{method:'POST',body:JSON.stringify({listing_id:id,quantity_qtl:+qty,delivery_mode:'SELLER_TRANSPORT',buyer_lat:19.076,buyer_lon:72.8777})});toast(`Order #${d.order_id} created • ${fmt(d.total)}`);closeModal();buyerOrders()}catch(e){toast(e.message)}}

async function buyerPreorders() {

  try {

    const [demands, linked] =
      await Promise.all([

        api(
          '/api/v2/v3/buyer-preorders/mine'
        ),

        api(
          '/api/v2/preorders?state=Tamil Nadu'
        )

      ]);


    const myDemands =
      Array.isArray(demands)
        ? demands
        : [];


    const myLinked =
      Array.isArray(linked)
        ? linked.filter(
            x =>
              Number(x.buyer_id)
              ===
              Number(me.id)
          )
        : [];


    $('content').innerHTML = `


      <div class="toolbar">

        <button
          class="primary"
          onclick="openCreateBuyerPreorder()"
        >
          ＋ Create Pre-Order Requirement
        </button>


        <span class="soft-note">

          Publish what you need.
          Matching farmers decide whether
          they want to supply it.

        </span>

      </div>



      <div class="hero-reco">

        <div>

          <small>
            BUYER DEMAND
          </small>

          <h2>
            Tell farmers what you want to buy
          </h2>

          <p>
            Your requirement remains open until
            farmers respond. No farmer's crop is
            reserved until you pay the secure
            booking token after acceptance.
          </p>

        </div>

      </div>



      ${section(
        '📢 My Published Requirements',

        myDemands.length

        ? myDemands.map(d => `


            <div class="preorder-card">


              <div class="harvest-top">

                <div>

                  <span class="crop-icon">
                    🛒
                  </span>

                  <b>

                    ${esc(d.crop)}
                    •
                    ${esc(
                      d.variety || 'Any'
                    )}

                  </b>

                </div>


                <span class="tag ${
                  d.status === 'FULFILLED'
                    ? 'success'
                    : ''
                }">

                  ${esc(d.status)}

                </span>

              </div>


              <p>

                Delivery:
                <b>

                  ${esc(
                    d.delivery_district || ''
                  )},

                  ${esc(
                    d.delivery_state
                    || 'Tamil Nadu'
                  )}

                </b>

              </p>


              <div class="mini-grid">


                <span>
                  Requested
                  <b>
                    ${num(d.quantity_qtl)} qtl
                  </b>
                </span>


                <span>
                  Remaining
                  <b>
                    ${num(
                      d.remaining_quantity_qtl
                    )} qtl
                  </b>
                </span>


                <span>
                  Your Offer
                  <b>
                    ${fmt(d.offer_price)}/qtl
                  </b>
                </span>


                <span>
                  Grade
                  <b>
                    ${esc(
                      d.grade_required || 'Any'
                    )}
                  </b>
                </span>


                <span>
                  Required By
                  <b>
                    ${esc(d.required_by_date)}
                  </b>
                </span>


                <span>
                  Token Offered
                  <b>
                    ${fmt(d.token_offer)}
                  </b>
                </span>


                <span>
                  Farmer Responses
                  <b>
                    ${num(
                      d.farmer_responses || 0
                    )}
                  </b>
                </span>


                <span>
                  Accepted Farmers
                  <b>
                    ${num(
                      d.accepted_farmers || 0
                    )}
                  </b>
                </span>


              </div>


              <div class="action-row">


                <button
                  class="primary"
                  onclick="
                    viewBuyerPreorderResponses(${d.id})
                  "
                >
                  👨‍🌾 View Farmer Responses
                </button>


              </div>


            </div>


          `).join('')

        : `

            <div class="empty">

              You have not published any
              pre-order requirements yet.

              <br><br>

              Click
              <b>+ Create Pre-Order Requirement</b>
              to tell farmers what you want.

            </div>

          `
      )}



      ${section(
        '🔐 Accepted Pre-Orders & Token Payments',

        myLinked.length

        ? myLinked.map(x => `


            <div class="preorder-card">


              <span class="tag ${
                x.status === 'ACCEPTED'
                  ? 'success'
                  : ''
              }">

                ${esc(x.status)}

              </span>


              <h3>

                ${esc(x.crop || 'Harvest')}

                •

                ${num(x.quantity_qtl)} qtl

              </h3>


              <p>

                Farmer:

                <b>
                  ${esc(
                    x.farmer_name || 'Farmer'
                  )}
                </b>

                •

                ${esc(
                  x.district || 'Tamil Nadu'
                )}

              </p>


              <div class="mini-grid">


                <span>
                  Agreed Price
                  <b>
                    ${fmt(x.offer_price)}/qtl
                  </b>
                </span>


                <span>
                  Fair Range
                  <b>
                    ${fmt(x.fair_low)}
                    –
                    ${fmt(x.fair_high)}
                  </b>
                </span>


                <span>
                  1 Day
                  <b>
                    ${fmt(x.predicted_1d)}
                  </b>
                </span>


                <span>
                  3 Days
                  <b>
                    ${fmt(x.predicted_3d)}
                  </b>
                </span>


                <span>
                  7 Days
                  <b>
                    ${fmt(x.predicted_7d)}
                  </b>
                </span>


                <span>
                  Secure Token
                  <b>
                    ${fmt(x.deposit_amount)}
                  </b>
                </span>


                <span>
                  Payment
                  <b>
                    ${esc(
                      x.token_payment_status
                      || 'UNPAID'
                    )}
                  </b>
                </span>


                <span>
                  GRAM AI
                  <b>
                    ${esc(
                      x.recommended_action
                      || '—'
                    )}
                  </b>
                </span>


              </div>


              ${
                x.status === 'AWAITING_TOKEN'

                ? `

                  <div class="info-panel">

                    The farmer has agreed to supply
                    this quantity.

                    Pay the secure token to reserve
                    the harvest.

                  </div>


                  <button
                    class="primary"
                    onclick="
                      payPreorderToken(${x.id})
                    "
                  >
                    🔒 Pay ${fmt(x.deposit_amount)} Token
                  </button>

                `

                : ''
              }


              ${
                x.status === 'ACCEPTED'

                ? `

                  <div class="verified-badge">

                    ✓ Token Paid — Harvest Reserved

                  </div>

                `

                : ''
              }


            </div>


          `).join('')

        : `

            <div class="empty">

              No farmer has accepted a
              pre-order yet.

            </div>

          `
      )}


    `;


  }

  catch (e) {

    $('content').innerHTML = `

      <div class="card error">
        ${esc(e.message)}
      </div>

    `;

  }

}

function openCreateBuyerPreorder() {


  const tomorrow =
    new Date();


  tomorrow.setDate(
    tomorrow.getDate() + 7
  );


  const defaultDate =
    tomorrow
      .toISOString()
      .split('T')[0];


  $('modalBody').innerHTML = `


    <div class="buyer-preorder-create">


      <span class="verified-badge">
        Buyer Demand Request
      </span>


      <h2>
        Create Pre-Order Requirement
      </h2>


      <p>

        Enter what you need.
        Matching farmers can choose whether
        they want to supply your requirement.

      </p>



      <div class="form-grid">


        <div class="field">

          <label>
            Crop *
          </label>

          <input
            id="bpCrop"
            class="control"
            placeholder="Tomato"
          >

        </div>



        <div class="field">

          <label>
            Variety
          </label>

          <input
            id="bpVariety"
            class="control"
            value="Any"
            placeholder="Premium / Small Onion / Any"
          >

        </div>



        <div class="field">

          <label>
            Grade Required
          </label>

          <select
            id="bpGrade"
            class="control"
          >

            <option value="Any">
              Any Grade
            </option>

            <option value="A">
              Grade A
            </option>

            <option value="B">
              Grade B
            </option>

            <option value="C">
              Grade C
            </option>

          </select>

        </div>



        <div class="field">

          <label>
            Required Quantity (qtl) *
          </label>

          <input
            id="bpQty"
            class="control"
            type="number"
            min="0.1"
            step="0.1"
            value="10"
          >

        </div>



        <div class="field">

          <label>
            Offer / Maximum Price ₹ per qtl *
          </label>

          <input
            id="bpPrice"
            class="control"
            type="number"
            min="1"
            value="2300"
          >

        </div>



        <div class="field">

          <label>
            Required By *
          </label>

          <input
            id="bpDate"
            class="control"
            type="date"
            value="${defaultDate}"
          >

        </div>



        <div class="field">

          <label>
            Delivery District
          </label>

          <input
            id="bpDistrict"
            class="control"
            value="${esc(
              me?.district || ''
            )}"
            placeholder="Coimbatore"
          >

        </div>



        <div class="field">

          <label>
            Delivery State
          </label>

          <input
            id="bpState"
            class="control"
            value="Tamil Nadu"
            readonly
          >

        </div>



        <div class="field">

          <label>
            Delivery Preference
          </label>

          <select
            id="bpDelivery"
            class="control"
          >

            <option value="BUYER_PICKUP">
              I will arrange pickup
            </option>

            <option value="FARMER_TRANSPORT">
              Farmer transport required
            </option>

            <option value="FLEXIBLE">
              Flexible
            </option>

          </select>

        </div>



        <div class="field">

          <label>
            Booking Token You Can Pay ₹
          </label>

          <input
            id="bpToken"
            class="control"
            type="number"
            min="0"
            value="500"
          >

          <small>

            This is paid only after a farmer
            accepts your requirement.

          </small>

        </div>


      </div>



      <div class="field">

        <label>
          Special Requirements
        </label>

        <textarea
          id="bpRequirements"
          class="control"
          rows="4"
          placeholder="Example: Grade A tomatoes, reusable crates preferred, delivery before 10 AM."
        ></textarea>

      </div>



      <div class="info-panel">

        <b>
          🔒 GRAM AI Pre-Order Rule
        </b>

        <p>

          Publishing this requirement does
          not force any farmer to sell.

          A farmer must first ACCEPT.
          Only then will secure token payment
          become available.

        </p>

      </div>



      <div class="action-row">


        <button
          class="secondary"
          onclick="closeModal()"
        >
          Cancel
        </button>


        <button
          class="primary"
          onclick="publishBuyerPreorder()"
        >
          📢 Publish Requirement
        </button>


      </div>


    </div>

  `;


  $('modal').classList.remove(
    'hidden'
  );

}

async function publishBuyerPreorder() {

  try {


    const crop =
      $('bpCrop')?.value
        ?.trim()
      || '';


    const variety =
      $('bpVariety')?.value
        ?.trim()
      || 'Any';


    const grade =
      $('bpGrade')?.value
      || 'Any';


    const quantity =
      Number(
        $('bpQty')?.value || 0
      );


    const price =
      Number(
        $('bpPrice')?.value || 0
      );


    const requiredDate =
      $('bpDate')?.value
      || '';


    const district =
      $('bpDistrict')?.value
        ?.trim()
      || '';


    const state =
      $('bpState')?.value
      || 'Tamil Nadu';


    const deliveryMode =
      $('bpDelivery')?.value
      || 'BUYER_PICKUP';


    const tokenOffer =
      Number(
        $('bpToken')?.value || 0
      );


    const requirements =
      $('bpRequirements')?.value
        ?.trim()
      || '';


    if (!crop) {

      throw new Error(
        'Enter the crop you want to buy'
      );

    }


    if (
      !quantity
      ||
      quantity <= 0
    ) {

      throw new Error(
        'Enter a valid required quantity'
      );

    }


    if (
      !price
      ||
      price <= 0
    ) {

      throw new Error(
        'Enter your offer price'
      );

    }


    if (!requiredDate) {

      throw new Error(
        'Select the required-by date'
      );

    }


    const result =
      await api(

        '/api/v2/v3/buyer-preorders',

        {

          method: 'POST',

          body: JSON.stringify({

            crop,

            variety,

            grade_required:
              grade,

            quantity_qtl:
              quantity,

            offer_price:
              price,

            required_by_date:
              requiredDate,

            delivery_district:
              district,

            delivery_state:
              state,

            delivery_mode:
              deliveryMode,

            token_offer:
              tokenOffer,

            special_requirements:
              requirements

          })

        }

      );


    closeModal();


    $('content').innerHTML = `


      <div class="order-success-page">


        <div class="order-success-card">


          <div class="success-tick">
            ✓
          </div>


          <span class="verified-badge">
            Pre-Order Published
          </span>


          <h2>
            Your Requirement is Live
          </h2>


          <p>

            Matching farmers can now view
            your requirement and decide
            whether they want to supply it.

          </p>


          <div class="mini-grid">


            <span>
              Crop
              <b>${esc(crop)}</b>
            </span>


            <span>
              Quantity
              <b>${num(quantity)} qtl</b>
            </span>


            <span>
              Offer
              <b>${fmt(price)}/qtl</b>
            </span>


            <span>
              Status
              <b>${esc(result.status || 'OPEN')}</b>
            </span>


          </div>


          <div class="info-panel">

            Farmers can now:

            <b>
              Accept • Decline • Negotiate • Chat
            </b>

          </div>


          <div class="action-row">

            <button
              class="primary"
              onclick="buyerPreorders()"
            >
              View My Pre-Orders
            </button>

          </div>


        </div>


      </div>

    `;


  }

  catch (e) {

    toast(e.message);

  }

}

async function viewBuyerPreorderResponses(
  demandId
) {

  try {


    const demands =
      await api(
        '/api/v2/v3/buyer-preorders/mine'
      );


    const d =
      demands.find(
        x =>
          Number(x.id) ===
          Number(demandId)
      );


    if (!d) {

      throw new Error(
        'Pre-order requirement not found'
      );

    }


    const responses =
      Array.isArray(d.responses)
        ? d.responses
        : [];


    $('modalBody').innerHTML = `


      <div class="buyer-response-page">


        <span class="verified-badge">
          Farmer Responses
        </span>


        <h2>
          ${esc(d.crop)}
          •
          ${num(d.quantity_qtl)} qtl
        </h2>


        <p>

          ${num(
            d.remaining_quantity_qtl
          )} qtl still required.

        </p>


        ${
          responses.length

          ? responses.map(r => `


              <div class="preorder-card">


                <div class="harvest-top">


                  <div>

                    <b>
                      👨‍🌾
                      ${esc(
                        r.farmer_name
                        || 'Farmer'
                      )}
                    </b>

                    <small>

                      ${esc(
                        r.farmer_district
                        || ''
                      )},

                      ${esc(
                        r.farmer_state
                        || 'Tamil Nadu'
                      )}

                    </small>

                  </div>


                  <span class="tag ${
                    r.action === 'ACCEPT'
                      ? 'success'
                      : ''
                  }">

                    ${esc(r.action)}

                  </span>


                </div>


                <div class="mini-grid">


                  <span>
                    Farmer Quantity
                    <b>
                      ${num(
                        r.quantity_qtl
                      )} qtl
                    </b>
                  </span>


                  <span>
                    Farmer Price
                    <b>

                      ${
                        r.farmer_price

                        ? `${fmt(
                            r.farmer_price
                          )}/qtl`

                        : '—'
                      }

                    </b>
                  </span>


                  <span>
                    Harvest
                    <b>
                      ${esc(
                        r.harvest_crop
                        || d.crop
                      )}
                    </b>
                  </span>


                  <span>
                    Grade
                    <b>
                      ${esc(
                        r.grade_expected
                        || '—'
                      )}
                    </b>
                  </span>


                  <span>
                    Harvest Date
                    <b>
                      ${esc(
                        r.expected_harvest_date
                        || '—'
                      )}
                    </b>
                  </span>


                </div>


                ${
                  r.message

                  ? `

                    <div class="info-panel">

                      ${esc(r.message)}

                    </div>

                  `

                  : ''
                }


                ${
                  r.action === 'ACCEPT'
                  &&
                  r.linked_preorder_id

                  ? `

                    <div class="verified-badge">

                      ✓ Farmer accepted —
                      Token payment available

                    </div>

                  `

                  : ''
                }


                <div class="action-row">


                  <button
                    class="secondary"
                    onclick="
                      openPreorderDemandChat(
                        ${r.farmer_id},
                        ${d.id},
                        false
                      )
                    "
                  >
                    💬 Chat
                  </button>


                  <button
                    class="secondary"
                    onclick="
                      openPreorderDemandChat(
                        ${r.farmer_id},
                        ${d.id},
                        true
                      )
                    "
                  >
                    🤝 Negotiate
                  </button>


                  ${
                    r.linked_preorder_id

                    ? `

                      <button
                        class="primary"
                        onclick="
                          closeModal();
                          buyerPreorders();
                        "
                      >
                        🔒 View Token Payment
                      </button>

                    `

                    : ''
                  }


                </div>


              </div>


            `).join('')

          : `

              <div class="empty">

                No farmer has responded yet.

                Your requirement remains
                visible to matching farmers.

              </div>

            `
        }


      </div>

    `;


    $('modal').classList.remove(
      'hidden'
    );


  }

  catch (e) {

    toast(e.message);

  }

}

async function openPreorderDemandChat(
  otherUserId,
  demandId,
  negotiation = false
) {

  try {


    if (!otherUserId) {

      throw new Error(
        'Farmer / buyer account unavailable for chat'
      );

    }


    /*
      Negative ID namespaces buyer-demand chats
      separately from normal preorder IDs.
      The chat table does not use a foreign-key
      constraint on preorder_id.
    */

    const chatPreorderId =
      -Math.abs(
        Number(demandId)
      );


    const firstMessage =
      negotiation

      ? `I would like to negotiate Buyer Pre-Order Requirement #${demandId}.`

      : `Regarding Buyer Pre-Order Requirement #${demandId}.`;


    await ensureChatWithBuyer(

      Number(otherUserId),

      null,

      chatPreorderId,

      firstMessage

    );


    localStorage.setItem(

      'gram_open_chat_user',

      String(otherUserId)

    );


    localStorage.setItem(

      'gram_open_chat_listing',

      ''

    );


    localStorage.setItem(

      'gram_open_preorder_demand',

      String(demandId)

    );


    if (negotiation) {

      localStorage.setItem(

        'gram_negotiation_offer',

        `BUYER_PREORDER_${demandId}`

      );

    }

    else {

      localStorage.removeItem(
        'gram_negotiation_offer'
      );

    }


    closeModal();


    route('chats');


  }

  catch (e) {

    toast(e.message);

  }

}

async function payPreorderToken(id) {

  try {


    const payment =
      await api(

        '/api/v2/payments/create',

        {

          method: 'POST',

          body: JSON.stringify({

            reference_type:
              'PREORDER',

            reference_id:
              Number(id),

            purpose:
              'BOOKING_TOKEN'

          })

        }

      );


    /*
      DEMO TEST MODE
    */

    if (
      String(payment.mode || '')
        .includes('DEMO')
    ) {


      const paymentId =
        payment.payment_record_id;


      const gatewayOrderId =
        payment.gateway_order_id;


      if (!paymentId) {

        throw new Error(
          'Payment record was not created'
        );

      }


      /*
        Demo client signature verification.
      */

      await api(

        `/api/v2/payments/${paymentId}/verify`,

        {

          method: 'POST',

          body: JSON.stringify({

            gateway_order_id:
              gatewayOrderId,

            gateway_payment_id:
              `pay_demo_${Date.now()}`,

            gateway_signature:
              'DEMO_SIGNATURE'

          })

        }

      );


      /*
        Trusted demo webhook.
      */

      await api(

        `/api/v2/payments/${paymentId}/demo-webhook`,

        {
          method: 'POST'
        }

      );


      /*
        Reserve farmer harvest only
        after secure payment reconciliation.
      */

      await api(

        `/api/v2/v3/preorders/${id}/activate-after-payment`,

        {
          method: 'POST'
        }

      );


      showPreorderPaymentSuccess(
        id,
        payment.amount_rupees
      );


      return;

    }


    /*
      REAL RAZORPAY TEST MODE
    */

    if (
      typeof Razorpay === 'undefined'
    ) {

      throw new Error(
        'Razorpay checkout library is not loaded'
      );

    }


    const options = {

      key:
        payment.key_id,

      amount:
        payment.amount_paise,

      currency:
        payment.currency || 'INR',

      name:
        'GRAM AI',

      description:
        `Secure Pre-Order Token #${id}`,

      order_id:
        payment.gateway_order_id,


      handler:
        async function(response) {

          try {


            await api(

              `/api/v2/payments/${payment.payment_record_id}/verify`,

              {

                method: 'POST',

                body: JSON.stringify({

                  gateway_order_id:
                    response.razorpay_order_id,

                  gateway_payment_id:
                    response.razorpay_payment_id,

                  gateway_signature:
                    response.razorpay_signature

                })

              }

            );


            toast(
              'Payment signature verified. Waiting for secure gateway reconciliation.'
            );


            buyerPreorders();


          }

          catch (e) {

            toast(e.message);

          }

        },


      theme: {
        color: '#15803d'
      }

    };


    const razorpay =
      new Razorpay(options);


    razorpay.open();


  }

  catch (e) {

    toast(e.message);

  }

}
function showPreorderPaymentSuccess(
  preorderId,
  amount
) {

  $('content').innerHTML = `


    <div class="order-success-page">


      <div class="order-success-card">


        <div class="success-tick">
          ✓
        </div>


        <span class="verified-badge">
          Token Payment Successful
        </span>


        <h2>
          Harvest Reserved
        </h2>


        <p>

          Your secure booking token has
          been reconciled successfully.

        </p>


        <div class="mini-grid">


          <span>

            Pre-Order

            <b>
              #${esc(preorderId)}
            </b>

          </span>


          <span>

            Token Paid

            <b>
              ${fmt(amount)}
            </b>

          </span>


          <span>

            Status

            <b>
              ACCEPTED
            </b>

          </span>


        </div>


        <div class="info-panel">

          ✓ The corresponding farmer harvest
          quantity is now reserved for this
          pre-order.

        </div>


        <div class="action-row">


          <button
            class="primary"
            onclick="buyerPreorders()"
          >
            View Pre-Orders
          </button>


          <button
            class="secondary"
            onclick="route('chats')"
          >
            💬 Open Chats
          </button>


        </div>


      </div>


    </div>

  `;

}




async function buyerOrders(){let os=await api('/api/orders');os=os.filter(o=>o.buyer_id===me.id);$('content').innerHTML=section(tr('orders'),os.length?os.map(o=>`<div class="order-card"><div><span class="tag">${esc(o.status)}</span><h3>Order #${o.id} • ${esc(o.crop)}</h3><p>${esc(o.district)}, Tamil Nadu • ${num(o.quantity_qtl)} qtl</p><div class="mini-grid"><span>Produce<b>${fmt(o.produce_total)}</b></span><span>${tr('transportCost')}<b>${fmt(o.transport_total)}</b></span><span>Total<b>${fmt(o.total)}</b></span><span>${tr('paymentStatus')}<b>${esc(o.status)}</b></span></div></div><div class="action-row"><button class="secondary" onclick="showTracking(${o.id})">📍 Track</button><button class="secondary" onclick="openComplaintForOrder(${o.id})">🛡 Complaint</button></div></div>`).join(''):'<div class="empty">No orders yet.</div>') }
async function showTracking(id){let t=await api(`/api/v2/v3/order-tracking/${id}`);$('modalBody').innerHTML=`<h2>${tr('tracking')} • #${id}</h2><div class="timeline">${t.map((x,i)=>`<div class="timeline-item ${i<2?'done':''}"><span></span><div><b>${esc(x.status)}</b><p>${esc(x.note)}</p><small>${esc(x.location_text)}</small></div></div>`).join('')}</div>`;$('modal').classList.remove('hidden')}
function openComplaintForOrder(id){route('grievances');setTimeout(()=>{if($('gdesc'))$('gdesc').value=`Issue regarding Order #${id}: `},80)}


async function buyerBulk() {

  $('content').innerHTML = `
    <div class="card">
      <h2>Loading Bulk & Shared Logistics...</h2>
    </div>
  `;

  try {

    let pools = [];
    let nearby = [];
    let routes = [];
    let bids = [];
    let invites = [];


    try {
      const data = await bulkApi(
        '/api/v2/v3/buyer-pools'
      );

      pools = Array.isArray(data)
        ? data
        : [];

    } catch (e) {

      console.error(
        '[Bulk] buyer-pools failed:',
        e
      );
    }


    try {
      const data = await bulkApi(
        '/api/v2/v3/nearby-buyers'
      );

      nearby = Array.isArray(data)
        ? data
        : [];

    } catch (e) {

      console.error(
        '[Bulk] nearby-buyers failed:',
        e
      );
    }


    try {
      const data = await bulkApi(
        '/api/v2/v3/route-share-options'
      );

      routes = Array.isArray(data)
        ? data
        : [];

    } catch (e) {

      console.error(
        '[Bulk] route-share-options failed:',
        e
      );
    }


    try {
      const data = await bulkApi(
        '/api/v2/v3/logistics-bids'
      );

      bids = Array.isArray(data)
        ? data
        : [];

    } catch (e) {

      console.error(
        '[Bulk] logistics-bids failed:',
        e
      );
    }


    try {
      const data = await bulkApi(
        '/api/v2/v3/buyer-pool-invites'
      );

      invites = Array.isArray(data)
        ? data
        : [];

    } catch (e) {

      console.error(
        '[Bulk] buyer-pool-invites failed:',
        e
      );
    }


    const myPools = pools.filter(
      p => p.is_owner || p.joined
    );

   $('content').innerHTML = `
      <div class="hero">
        <div>
          <div class="eyebrow">BUY TOGETHER • MOVE TOGETHER</div>
          <h1>Bulk & Shared Logistics</h1>
          <p>
            Combine purchases with verified buyers and share
            transport capacity to reduce procurement and delivery cost.
          </p>
        </div>

        <div class="actions">
          <button class="primary" onclick="openCreateBulkOrder()">
            + Create Bulk Order
          </button>

          <button class="secondary" onclick="openJoinBulkOrder()">
            🔑 Join With Code
          </button>
        </div>
      </div>


      <div class="grid3">
        <div class="card">
          <div class="muted">My Bulk Orders</div>
          <h2>${myPools.length}</h2>
        </div>

        <div class="card">
          <div class="muted">Nearby Buyers</div>
          <h2>${nearby.length}</h2>
        </div>

        <div class="card">
          <div class="muted">My Logistics Bids</div>
          <h2>${bids.length}</h2>
        </div>
      </div>


      ${invites.filter(x => x.status === 'PENDING').length ? `
        <div class="card">
          <h2>📩 Bulk Purchase Invitations</h2>
          <p class="muted">
            Other buyers have invited you to combine purchases.
          </p>

          <div class="cards">
            ${invites.filter(x => x.status === 'PENDING').map(i => `
              <div class="card soft">
                <div class="row between">
                  <div>
                    <b>${esc(i.pool_name)}</b>
                    <div class="muted">
                      Invited by ${esc(i.invited_by_name)}
                    </div>
                  </div>

                  <span class="pill">PENDING</span>
                </div>

                <hr>

                <div class="grid3">
                  <div>
                    <span class="muted">Crop</span>
                    <b>${esc(i.crop)}</b>
                  </div>

                  <div>
                    <span class="muted">Target</span>
                    <b>${num(i.target_qtl)} qtl</b>
                  </div>

                  <div>
                    <span class="muted">Suggested Qty</span>
                    <b>${num(i.proposed_quantity_qtl)} qtl</b>
                  </div>
                </div>

                <div class="actions">
                  <button class="primary"
                    onclick="respondBulkInvite(${i.id},'ACCEPT',${Number(i.proposed_quantity_qtl || 0)})">
                    Accept
                  </button>

                  <button class="secondary"
                    onclick="respondBulkInvite(${i.id},'DECLINE',0)">
                    Decline
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}


      <div class="card">
        <div class="row between">
          <div>
            <h2>🛒 My Bulk Orders</h2>
            <p class="muted">
              Track quantity, members, join code and procurement status.
            </p>
          </div>

          <button class="primary" onclick="openCreateBulkOrder()">
            + Create
          </button>
        </div>

        ${myPools.length ? `
          <div class="cards">
            ${myPools.map(p => {
              const percent = Math.min(
                100,
                Math.round(
                  Number(p.current_qtl || 0) /
                  Math.max(1, Number(p.target_qtl || 1)) * 100
                )
              );

              return `
                <div class="card soft">
                  <div class="row between">
                    <div>
                      <h3>${esc(p.name)}</h3>
                      <div class="muted">
                        ${esc(p.crop)} • ${esc(p.variety || 'Any')}
                        • Grade ${esc(p.grade_required || 'Any')}
                      </div>
                    </div>

                    <span class="pill">
                      ${esc(p.status)}
                    </span>
                  </div>

                  <div style="margin:14px 0">
                    <div class="row between">
                      <span>
                        ${num(p.current_qtl)} / ${num(p.target_qtl)} qtl
                      </span>
                      <b>${percent}%</b>
                    </div>

                    <div class="progress">
                      <div style="width:${percent}%"></div>
                    </div>
                  </div>

                  <div class="grid3">
                    <div>
                      <span class="muted">Remaining</span>
                      <b>${num(p.remaining_qtl)} qtl</b>
                    </div>

                    <div>
                      <span class="muted">Members</span>
                      <b>${p.members || 1}</b>
                    </div>

                    <div>
                      <span class="muted">Target Price</span>
                      <b>₹${num(p.target_price)}/qtl</b>
                    </div>
                  </div>

                  ${p.is_owner ? `
                    <div class="card" style="margin-top:12px">
                      <span class="muted">Buyer Join Code</span>
                      <h2>${esc(p.join_code || '—')}</h2>

                      <button class="secondary"
                        onclick="copyBulkCode('${esc(p.join_code || '')}')">
                        📋 Copy Code
                      </button>
                    </div>
                  ` : ''}

                  <div class="actions">
                    <button class="primary"
                      onclick="viewBulkOrder(${p.id})">
                      View Full Details
                    </button>

                    ${p.is_owner ? `
                      <button class="secondary"
                        onclick="openAddBuyerToBulk(${p.id})">
                        + Add Buyer
                      </button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        ` : `
          <div class="empty">
            No bulk orders yet.
            Create one or join another buyer using a code.
          </div>
        `}
      </div>


      <div class="card">
        <h2>👥 Nearby Buyers</h2>
        <p class="muted">
          Connect with buyers around your procurement area,
          chat with them or combine a purchase.
        </p>

        ${nearby.length ? `
          <div class="cards">
            ${nearby.slice(0,12).map(b => `
              <div class="card soft">
                <div class="row between">
                  <div>
                    <h3>${esc(b.name)}</h3>
                    <div class="muted">
                      📍 ${esc(b.district || 'Tamil Nadu')},
                      ${esc(b.state || 'Tamil Nadu')}
                    </div>
                  </div>

                  <span class="pill">Verified Buyer</span>
                </div>

                <div class="grid3">
                  <div>
                    <span class="muted">Reliability</span>
                    <b>${num(b.buyer_reliability)}%</b>
                  </div>

                  <div>
                    <span class="muted">Payment</span>
                    <b>${num(b.instant_payment)}%</b>
                  </div>

                  <div>
                    <span class="muted">Zero Cancel</span>
                    <b>${b.zero_cancel_streak || 0}</b>
                  </div>
                </div>

                <div class="actions">
                  <button class="secondary"
                    onclick="openNearbyBuyerProfile(${b.id})">
                    View Profile
                  </button>

                  <button class="secondary"
                    onclick="openBulkBuyerChat(${b.id})">
                    💬 Chat
                  </button>

                  <button class="primary"
                    onclick="openCombineBuyer(${b.id},'${esc(b.name)}')">
                    🤝 Combine Purchase
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="empty">
            No nearby buyers available.
          </div>
        `}
      </div>


      <div class="card">
        <h2>🚚 Route-Share Capacity</h2>
        <p class="muted">
          Find spare vehicle capacity and submit a detailed transport bid.
        </p>

        ${routes.length ? `
          <div class="cards">
            ${routes.map(t => `
              <div class="card soft">
                <div class="row between">
                  <div>
                    <h3>${esc(t.name)}</h3>
                    <div class="muted">
                      ${esc(t.vehicle_type || 'Transport Vehicle')}
                    </div>
                  </div>

                  <span class="pill">
                    ${esc(t.route_share_status || 'AVAILABLE')}
                  </span>
                </div>

                <div class="grid3">
                  <div>
                    <span class="muted">Capacity</span>
                    <b>${num(t.available_capacity_qtl)} qtl</b>
                  </div>

                  <div>
                    <span class="muted">Rate</span>
                    <b>₹${num(t.rate_per_km)}/km</b>
                  </div>

                  <div>
                    <span class="muted">Rating</span>
                    <b>⭐ ${num(t.rating)}</b>
                  </div>
                </div>

                <button class="primary"
                  onclick="openRouteShareBid(${t.id})">
                  View Route & Bid
                </button>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="empty">
            No route-share capacity currently available.
          </div>
        `}
      </div>


      <div class="card">
        <h2>📑 My Route-Share Bids</h2>

        ${bids.length ? `
          <div class="cards">
            ${bids.map(b => `
              <div class="card soft">
                <div class="row between">
                  <div>
                    <b>${esc(b.transporter_name)}</b>
                    <div class="muted">
                      ${esc(b.pickup_location)} →
                      ${esc(b.delivery_location)}
                    </div>
                  </div>

                  <span class="pill">${esc(b.status)}</span>
                </div>

                <div class="grid3">
                  <div>
                    <span class="muted">Quantity</span>
                    <b>${num(b.quantity_qtl)} qtl</b>
                  </div>

                  <div>
                    <span class="muted">Your Bid</span>
                    <b>₹${num(b.proposed_bid)}</b>
                  </div>

                  <div>
                    <span class="muted">Code</span>
                    <b>${esc(b.confirmation_code)}</b>
                  </div>
                </div>

                <button class="secondary"
                  onclick="viewLogisticsBid(${b.id})">
                  View Bid
                </button>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="empty">
            You have not submitted a logistics bid yet.
          </div>
        `}
      </div>
    `;
  } catch (e) {
    $('content').innerHTML = `
      <div class="card">
        <h2>Bulk & Shared Logistics</h2>
        <div class="alert danger">
          ${esc(e.message)}
        </div>
      </div>
    `;
  }
}


async function bulkApi(path, timeout = 3000) {
  let timer;

  try {
    return await Promise.race([
      api(path),

      new Promise((_, reject) => {
        timer = setTimeout(() => {
          reject(
            new Error(`Timeout: ${path}`)
          );
        }, timeout);
      })
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function openCreateBulkOrder() {
  $('pageTitle').textContent = 'Create Bulk Order';

  const date = new Date();
  date.setDate(date.getDate() + 7);

  $('content').innerHTML = `
    <div class="hero">
      <div>
        <div class="eyebrow">COLLECTIVE PROCUREMENT</div>
        <h1>Create Bulk Order</h1>
        <p>
          Create a group purchase and invite other buyers directly
          or let them join using your unique code.
        </p>
      </div>
    </div>

    <div class="card">
      <h2>1. Purchase Requirement</h2>

      <div class="form-grid">
        <label>
          Bulk Order Name
          <input id="bulkName"
            placeholder="Example: Coimbatore Tomato Bulk Buy">
        </label>

        <label>
          Crop
          <input id="bulkCrop"
            placeholder="Tomato">
        </label>

        <label>
          Variety
          <input id="bulkVariety"
            placeholder="Any / Hybrid">
        </label>

        <label>
          Required Grade
          <select id="bulkGrade">
            <option>Any</option>
            <option>A</option>
            <option>B</option>
            <option>C</option>
          </select>
        </label>

        <label>
          Your Quantity (qtl)
          <input id="bulkMyQty"
            type="number"
            min="0.1"
            step="0.1">
        </label>

        <label>
          Target Group Quantity (qtl)
          <input id="bulkTargetQty"
            type="number"
            min="0.1"
            step="0.1">
        </label>

        <label>
          Target Price ₹/qtl
          <input id="bulkTargetPrice"
            type="number"
            min="0">
        </label>

        <label>
          Required By
          <input id="bulkDate"
            type="date"
            value="${date.toISOString().slice(0,10)}">
        </label>

        <label>
          District
          <input id="bulkDistrict"
            value="${esc(me?.district || 'Coimbatore')}">
        </label>

        <label>
          Delivery Location
          <input id="bulkDelivery"
            placeholder="Warehouse / market / address">
        </label>

        <label>
          Transport Preference
          <select id="bulkTransport">
            <option value="SHARED_LOGISTICS">
              Shared Logistics
            </option>
            <option value="BUYER_PICKUP">
              Buyer Pickup
            </option>
            <option value="FARMER_TRANSPORT">
              Farmer Transport
            </option>
            <option value="FLEXIBLE">
              Flexible
            </option>
          </select>
        </label>
      </div>

      <label>
        Special Requirements
        <textarea id="bulkRequirements"
          placeholder="Packaging, quality, delivery window, etc."></textarea>
      </label>

      <div class="actions">
        <button class="secondary" onclick="buyerBulk()">
          Cancel
        </button>

        <button class="primary" onclick="reviewBulkOrder()">
          Review Bulk Order →
        </button>
      </div>
    </div>
  `;
}

function reviewBulkOrder() {
  const data = {
    name: document.getElementById('bulkName').value.trim(),
    crop: document.getElementById('bulkCrop').value.trim(),
    variety: document.getElementById('bulkVariety').value.trim() || 'Any',
    grade_required: document.getElementById('bulkGrade').value,
    quantity_qtl: Number(document.getElementById('bulkMyQty').value),
    target_qtl: Number(document.getElementById('bulkTargetQty').value),
    target_price: Number(document.getElementById('bulkTargetPrice').value || 0),
    required_by_date: document.getElementById('bulkDate').value,
    district: document.getElementById('bulkDistrict').value.trim(),
    delivery_location: document.getElementById('bulkDelivery').value.trim(),
    transport_preference: document.getElementById('bulkTransport').value,
    special_requirements: document.getElementById('bulkRequirements').value.trim()
  };

  if (!data.name || !data.crop || !data.district) {
    toast('Enter bulk order name, crop and district.');
    return;
  }

  if (data.quantity_qtl <= 0 || data.target_qtl <= 0) {
    toast('Enter valid quantities.');
    return;
  }

  if (data.quantity_qtl > data.target_qtl) {
    toast('Your quantity cannot exceed target quantity.');
    return;
  }

  window.pendingBulkOrder = data;

  $('content').innerHTML = `
    <div class="hero">
      <div>
        <div class="eyebrow">FINAL CHECK</div>
        <h1>Confirm Bulk Order</h1>
        <p>
          Review the complete requirement before publishing it.
        </p>
      </div>
    </div>

    <div class="card">
      <h2>${esc(data.name)}</h2>

      <div class="grid3">
        <div>
          <span class="muted">Crop</span>
          <b>${esc(data.crop)}</b>
        </div>

        <div>
          <span class="muted">Variety</span>
          <b>${esc(data.variety)}</b>
        </div>

        <div>
          <span class="muted">Grade</span>
          <b>${esc(data.grade_required)}</b>
        </div>

        <div>
          <span class="muted">Your Quantity</span>
          <b>${num(data.quantity_qtl)} qtl</b>
        </div>

        <div>
          <span class="muted">Group Target</span>
          <b>${num(data.target_qtl)} qtl</b>
        </div>

        <div>
          <span class="muted">Target Price</span>
          <b>₹${num(data.target_price)}/qtl</b>
        </div>

        <div>
          <span class="muted">Required By</span>
          <b>${esc(data.required_by_date)}</b>
        </div>

        <div>
          <span class="muted">District</span>
          <b>${esc(data.district)}</b>
        </div>

        <div>
          <span class="muted">Transport</span>
          <b>${esc(data.transport_preference)}</b>
        </div>
      </div>

      <hr>

      <b>Delivery</b>
      <p>${esc(data.delivery_location || 'Not specified')}</p>

      <b>Special Requirements</b>
      <p>${esc(data.special_requirements || 'None')}</p>

      <div class="alert">
        After creation, GRAM AI will generate a unique
        join code that you can share with other buyers.
      </div>

      <div class="actions">
        <button class="secondary" onclick="openCreateBulkOrder()">
          ← Edit
        </button>

        <button class="primary" onclick="submitBulkOrder()">
          ✓ Confirm & Create
        </button>
      </div>
    </div>
  `;
}

async function submitBulkOrder() {
  try {
    if (!window.pendingBulkOrder) {
      throw new Error('Bulk order information is missing.');
    }

    const result = await api('/api/v2/v3/buyer-pools', {
      method: 'POST',
      body: JSON.stringify(window.pendingBulkOrder)
    });

    window.pendingBulkOrder = null;

    $('content').innerHTML = `
      <div class="card success-card">
        <div style="font-size:54px">✅</div>

        <h1>Bulk Order Created</h1>

        <p>
          Your group purchase is now open for other buyers.
        </p>

        <div class="card">
          <span class="muted">Bulk Order ID</span>
          <h2>#${result.id}</h2>

          <span class="muted">Unique Join Code</span>
          <h1>${esc(result.join_code)}</h1>

          <button class="secondary"
            onclick="copyBulkCode('${esc(result.join_code)}')">
            📋 Copy Join Code
          </button>
        </div>

        <div class="grid3">
          <div>
            <span class="muted">Your Quantity</span>
            <b>${num(result.current_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Target</span>
            <b>${num(result.target_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Remaining</span>
            <b>${num(result.remaining_qtl)} qtl</b>
          </div>
        </div>

        <div class="actions">
          <button class="primary"
            onclick="openAddBuyerToBulk(${result.id})">
            + Add Another Buyer
          </button>

          <button class="secondary" onclick="buyerBulk()">
            Back to Bulk & Logistics
          </button>
        </div>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}


function copyBulkCode(code) {
  if (!code) return;

  navigator.clipboard.writeText(code)
    .then(() => toast('Join code copied'))
    .catch(() => toast(`Join code: ${code}`));
}

function openJoinBulkOrder() {
  modal(`
    <h2>🔑 Join Bulk Order</h2>

    <p class="muted">
      Enter the join code shared by another buyer.
    </p>

    <label>
      Join Code
      <input id="joinBulkCode"
        placeholder="Example: GB-7K4P92">
    </label>

    <label>
      Your Quantity (qtl)
      <input id="joinBulkQty"
        type="number"
        min="0.1"
        step="0.1">
    </label>

    <div class="actions">
      <button class="secondary" onclick="closeModal()">
        Cancel
      </button>

      <button class="primary" onclick="submitJoinBulkCode()">
        Review & Join
      </button>
    </div>
  `);
}


async function submitJoinBulkCode() {
  try {
    const join_code =
      document.getElementById('joinBulkCode').value.trim();

    const quantity_qtl =
      Number(document.getElementById('joinBulkQty').value);

    if (!join_code || quantity_qtl <= 0) {
      throw new Error('Enter join code and quantity.');
    }

    const result = await api(
      '/api/v2/v3/buyer-pools/join-by-code',
      {
        method: 'POST',
        body: JSON.stringify({
          join_code,
          quantity_qtl
        })
      }
    );

    closeModal();

    $('content').innerHTML = `
      <div class="card success-card">
        <div style="font-size:54px">🤝</div>

        <h1>Bulk Order Joined</h1>

        <p>
          You are now part of this combined purchase.
        </p>

        <div class="card">
          <b>Bulk Order #${result.pool_id}</b>
          <p>
            Quantity committed:
            <strong>${num(result.my_quantity_qtl)} qtl</strong>
          </p>
          <p>
            Status:
            <strong>${esc(result.bulk_status)}</strong>
          </p>
        </div>

        <button class="primary" onclick="buyerBulk()">
          View My Bulk Orders
        </button>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}

async function viewBulkOrder(poolId) {
  try {
    const p = await api(`/api/v2/v3/buyer-pools/${poolId}`);

    $('content').innerHTML = `
      <div class="hero">
        <div>
          <div class="eyebrow">BULK ORDER #${p.id}</div>
          <h1>${esc(p.name)}</h1>
          <p>
            ${esc(p.crop)} • ${esc(p.variety || 'Any')}
            • Grade ${esc(p.grade_required || 'Any')}
          </p>
        </div>

        <button class="secondary" onclick="buyerBulk()">
          ← Back
        </button>
      </div>

      <div class="card">
        <div class="grid3">
          <div>
            <span class="muted">Target</span>
            <b>${num(p.target_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Committed</span>
            <b>${num(p.current_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Remaining</span>
            <b>${num(p.remaining_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Target Price</span>
            <b>₹${num(p.target_price)}/qtl</b>
          </div>

          <div>
            <span class="muted">Required By</span>
            <b>${esc(p.required_by_date || '—')}</b>
          </div>

          <div>
            <span class="muted">Status</span>
            <b>${esc(p.status)}</b>
          </div>
        </div>

        <hr>

        <h3>Join Code</h3>
        <h2>${esc(p.join_code)}</h2>

        <button class="secondary"
          onclick="copyBulkCode('${esc(p.join_code)}')">
          📋 Copy Code
        </button>
      </div>

      <div class="card">
        <h2>👥 Participating Buyers</h2>

        ${(p.members_detail || []).map(m => `
          <div class="card soft">
            <div class="row between">
              <div>
                <b>${esc(m.buyer_name)}</b>
                <div class="muted">
                  ${esc(m.district || '')},
                  ${esc(m.state || '')}
                </div>
              </div>

              <strong>
                ${num(m.quantity_qtl)} qtl
              </strong>
            </div>
          </div>
        `).join('')}
      </div>

      <div class="actions">
        <button class="primary"
          onclick="openAddBuyerToBulk(${p.id})">
          + Invite Buyer
        </button>

        <button class="secondary" onclick="buyerBulk()">
          Done
        </button>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}

async function openAddBuyerToBulk(poolId) {
  try {
    const buyers = await api('/api/v2/v3/nearby-buyers');

    modal(`
      <h2>👥 Add Buyer to Bulk Order</h2>

      <p class="muted">
        Select a nearby buyer and send them an invitation.
        They can also join independently using your join code.
      </p>

      <label>
        Buyer
        <select id="bulkInviteBuyer">
          <option value="">Select Buyer</option>

          ${buyers.map(b => `
            <option value="${b.id}">
              ${esc(b.name)} — ${esc(b.district || 'Tamil Nadu')}
            </option>
          `).join('')}
        </select>
      </label>

      <label>
        Suggested Quantity (qtl)
        <input id="bulkInviteQty"
          type="number"
          min="0"
          step="0.1">
      </label>

      <label>
        Message
        <textarea id="bulkInviteMessage"
          placeholder="Would you like to combine this purchase with me?"></textarea>
      </label>

      <div class="actions">
        <button class="secondary" onclick="closeModal()">
          Cancel
        </button>

        <button class="primary"
          onclick="sendBulkBuyerInvite(${poolId})">
          Send Invitation
        </button>
      </div>
    `);
  } catch (e) {
    toast(e.message);
  }
}


async function sendBulkBuyerInvite(poolId) {
  try {
    const buyer_id =
      Number(document.getElementById('bulkInviteBuyer').value);

    const quantity_qtl =
      Number(document.getElementById('bulkInviteQty').value || 0);

    const message =
      document.getElementById('bulkInviteMessage').value.trim();

    if (!buyer_id) {
      throw new Error('Select a buyer.');
    }

    const result = await api(
      `/api/v2/v3/buyer-pools/${poolId}/invite`,
      {
        method: 'POST',
        body: JSON.stringify({
          buyer_id,
          quantity_qtl,
          message
        })
      }
    );

    closeModal();

    toast(
      `Invitation sent to ${result.buyer_name}`
    );
  } catch (e) {
    toast(e.message);
  }
}

async function respondBulkInvite(id, action, suggestedQty) {
  try {
    let quantity = suggestedQty;

    if (action === 'ACCEPT' && quantity <= 0) {
      quantity = Number(
        prompt('Enter quantity you want to combine (qtl):') || 0
      );

      if (quantity <= 0) return;
    }

    await api(`/api/v2/v3/buyer-pool-invites/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        action,
        quantity_qtl:
          action === 'ACCEPT' ? quantity : null
      })
    });

    toast(
      action === 'ACCEPT'
        ? 'Bulk invitation accepted'
        : 'Invitation declined'
    );

    buyerBulk();
  } catch (e) {
    toast(e.message);
  }
}

async function openNearbyBuyerProfile(buyerId) {
  try {
    const buyers = await api('/api/v2/v3/nearby-buyers');

    const b = buyers.find(
      x => Number(x.id) === Number(buyerId)
    );

    if (!b) throw new Error('Buyer not found.');

    modal(`
      <h2>${esc(b.name)}</h2>

      <span class="pill">Verified Buyer</span>

      <div class="grid3">
        <div>
          <span class="muted">Location</span>
          <b>${esc(b.district || '')}, ${esc(b.state || '')}</b>
        </div>

        <div>
          <span class="muted">Reliability</span>
          <b>${num(b.buyer_reliability)}%</b>
        </div>

        <div>
          <span class="muted">Payment Score</span>
          <b>${num(b.instant_payment)}%</b>
        </div>
      </div>

      <div class="actions">
        <button class="secondary"
          onclick="openBulkBuyerChat(${b.id})">
          💬 Chat
        </button>

        <button class="primary"
          onclick="closeModal();openCombineBuyer(${b.id},'${esc(b.name)}')">
          🤝 Combine Purchase
        </button>
      </div>
    `);
  } catch (e) {
    toast(e.message);
  }
}


async function openBulkBuyerChat(buyerId) {
  try {
    await ensureChatWithBuyer(
      Number(buyerId),
      null,
      null,
      'Hi, I would like to discuss a combined bulk purchase.'
    );

    localStorage.setItem(
      'gram_open_chat_user',
      String(buyerId)
    );

    closeModal();
    route('chats');
  } catch (e) {
    toast(e.message);
  }
}

async function openCombineBuyer(buyerId, buyerName) {
  try {
    const pools = await api('/api/v2/v3/buyer-pools');

    const mine = pools.filter(p => p.is_owner);

    if (!mine.length) {
      $('content').innerHTML = `
        <div class="card">
          <h2>🤝 Combine with ${esc(buyerName)}</h2>

          <p>
            Create a bulk order first, then invite
            ${esc(buyerName)} to join it.
          </p>

          <div class="actions">
            <button class="primary" onclick="openCreateBulkOrder()">
              + Create Bulk Order
            </button>

            <button class="secondary" onclick="buyerBulk()">
              Cancel
            </button>
          </div>
        </div>
      `;
      return;
    }

    modal(`
      <h2>🤝 Combine Purchase</h2>

      <p>
        Invite <strong>${esc(buyerName)}</strong>
        to one of your bulk orders.
      </p>

      <label>
        Select Bulk Order
        <select id="combinePool">
          ${mine.map(p => `
            <option value="${p.id}">
              ${esc(p.name)} —
              ${esc(p.crop)} —
              ${num(p.remaining_qtl)} qtl remaining
            </option>
          `).join('')}
        </select>
      </label>

      <label>
        Suggested Quantity (qtl)
        <input id="combineQty"
          type="number"
          min="0"
          step="0.1">
      </label>

      <label>
        Message
        <textarea id="combineMessage">
Let's combine this purchase and reduce procurement/logistics cost.
        </textarea>
      </label>

      <div class="actions">
        <button class="secondary" onclick="closeModal()">
          Cancel
        </button>

        <button class="primary"
          onclick="sendCombineBuyerInvite(${buyerId})">
          Send Combine Request
        </button>
      </div>
    `);
  } catch (e) {
    toast(e.message);
  }
}


async function sendCombineBuyerInvite(buyerId) {
  try {
    const poolId =
      Number(document.getElementById('combinePool').value);

    const quantity_qtl =
      Number(document.getElementById('combineQty').value || 0);

    const message =
      document.getElementById('combineMessage').value.trim();

    await api(
      `/api/v2/v3/buyer-pools/${poolId}/invite`,
      {
        method: 'POST',
        body: JSON.stringify({
          buyer_id: Number(buyerId),
          quantity_qtl,
          message
        })
      }
    );

    closeModal();

    $('content').innerHTML = `
      <div class="card success-card">
        <div style="font-size:54px">🤝</div>

        <h1>Combine Request Sent</h1>

        <p>
          The buyer can accept your invitation and
          add their quantity to the bulk purchase.
        </p>

        <button class="primary" onclick="buyerBulk()">
          Back to Bulk Orders
        </button>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}

async function openRouteShareBid(transporterId) {
  try {
    const routes = await api('/api/v2/v3/route-share-options');

    const t = routes.find(
      x => Number(x.id) === Number(transporterId)
    );

    if (!t) {
      throw new Error('Transporter not found.');
    }

    const pools = await api('/api/v2/v3/buyer-pools');

    const myPools = pools.filter(p => p.joined);

    const date = new Date();
    date.setDate(date.getDate() + 1);

    $('content').innerHTML = `
      <div class="hero">
        <div>
          <div class="eyebrow">ROUTE SHARE • CAPACITY BIDDING</div>
          <h1>${esc(t.name)}</h1>
          <p>
            Review vehicle capacity and submit your transport bid.
          </p>
        </div>

        <button class="secondary" onclick="buyerBulk()">
          ← Back
        </button>
      </div>


      <div class="card">
        <h2>🚚 Vehicle & Transporter</h2>

        <div class="grid3">
          <div>
            <span class="muted">Vehicle</span>
            <b>${esc(t.vehicle_type || 'Transport Vehicle')}</b>
          </div>

          <div>
            <span class="muted">Vehicle Number</span>
            <b>${esc(t.vehicle_number || '—')}</b>
          </div>

          <div>
            <span class="muted">Rating</span>
            <b>⭐ ${num(t.rating)}</b>
          </div>

          <div>
            <span class="muted">Capacity</span>
            <b>${num(t.available_capacity_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Rate</span>
            <b>₹${num(t.rate_per_km)}/km</b>
          </div>

          <div>
            <span class="muted">GPS</span>
            <b>Available for confirmed booking</b>
          </div>
        </div>
      </div>


      <div class="card">
        <h2>📍 Route Details</h2>

        <div class="form-grid">
          <label>
            Link Bulk Order
            <select id="bidPool">
              <option value="">No linked bulk order</option>

              ${myPools.map(p => `
                <option value="${p.id}">
                  ${esc(p.name)} — ${esc(p.crop)}
                </option>
              `).join('')}
            </select>
          </label>

          <label>
            Crop
            <input id="bidCrop"
              placeholder="Tomato">
          </label>

          <label>
            Quantity (qtl)
            <input id="bidQty"
              type="number"
              min="0.1"
              step="0.1">
          </label>

          <label>
            Estimated Distance (km)
            <input id="bidDistance"
              type="number"
              min="0"
              oninput="updateRouteBidEstimate(${Number(t.rate_per_km || 0)})">
          </label>

          <label>
            Pickup Location
            <input id="bidPickup"
              placeholder="Example: Coimbatore Market Yard">
          </label>

          <label>
            Delivery Location
            <input id="bidDelivery"
              placeholder="Example: Chennai Warehouse">
          </label>

          <label>
            Pickup Date
            <input id="bidDate"
              type="date"
              value="${date.toISOString().slice(0,10)}">
          </label>

          <label>
            Pickup Time
            <input id="bidTime"
              type="time">
          </label>

          <label>
            Your Bid ₹
            <input id="bidAmount"
              type="number"
              min="1">
          </label>
        </div>

        <label>
          Special Instructions
          <textarea id="bidInstructions"
            placeholder="Loading requirement, cold storage, packaging, timing, etc."></textarea>
        </label>

        <div class="card soft">
          <h3>Estimated Route Cost</h3>

          <div id="routeBidEstimate">
            Enter distance to calculate estimate.
          </div>
        </div>

        <div class="actions">
          <button class="secondary" onclick="buyerBulk()">
            Cancel
          </button>

          <button class="primary"
            onclick="reviewRouteShareBid(${t.id},'${esc(t.name)}',${Number(t.rate_per_km || 0)})">
            Review Bid →
          </button>
        </div>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}

function updateRouteBidEstimate(rate) {
  const distance =
    Number(document.getElementById('bidDistance')?.value || 0);

  const cost = distance * Number(rate || 0);

  const box = document.getElementById('routeBidEstimate');

  if (!box) return;

  box.innerHTML = `
    <div class="grid3">
      <div>
        <span class="muted">Distance</span>
        <b>${num(distance)} km</b>
      </div>

      <div>
        <span class="muted">Rate</span>
        <b>₹${num(rate)}/km</b>
      </div>

      <div>
        <span class="muted">Estimated Cost</span>
        <b>₹${num(cost)}</b>
      </div>
    </div>
  `;
}

function reviewRouteShareBid(transporterId, transporterName, rate) {
  const data = {
    transporter_id: Number(transporterId),
    pool_id:
      Number(document.getElementById('bidPool').value) || null,

    crop:
      document.getElementById('bidCrop').value.trim(),

    quantity_qtl:
      Number(document.getElementById('bidQty').value),

    pickup_location:
      document.getElementById('bidPickup').value.trim(),

    delivery_location:
      document.getElementById('bidDelivery').value.trim(),

    pickup_date:
      document.getElementById('bidDate').value,

    pickup_time:
      document.getElementById('bidTime').value,

    proposed_bid:
      Number(document.getElementById('bidAmount').value),

    estimated_distance_km:
      Number(document.getElementById('bidDistance').value || 0),

    special_instructions:
      document.getElementById('bidInstructions').value.trim()
  };

  if (
    data.quantity_qtl <= 0 ||
    !data.pickup_location ||
    !data.delivery_location ||
    !data.pickup_date ||
    data.proposed_bid <= 0
  ) {
    toast('Complete quantity, route, date and bid amount.');
    return;
  }

  window.pendingRouteBid = data;

  const estimate =
    data.estimated_distance_km * Number(rate || 0);

  $('content').innerHTML= `
    <div class="hero">
      <div>
        <div class="eyebrow">CONFIRM TRANSPORT BID</div>
        <h1>Review Route-Share Bid</h1>
        <p>
          Confirm the complete logistics request before sending it.
        </p>
      </div>
    </div>

    <div class="card">
      <h2>🚚 ${esc(transporterName)}</h2>

      <div class="grid3">
        <div>
          <span class="muted">Crop</span>
          <b>${esc(data.crop || 'Mixed Produce')}</b>
        </div>

        <div>
          <span class="muted">Quantity</span>
          <b>${num(data.quantity_qtl)} qtl</b>
        </div>

        <div>
          <span class="muted">Distance</span>
          <b>${num(data.estimated_distance_km)} km</b>
        </div>

        <div>
          <span class="muted">Rate Reference</span>
          <b>₹${num(rate)}/km</b>
        </div>

        <div>
          <span class="muted">Estimated Cost</span>
          <b>₹${num(estimate)}</b>
        </div>

        <div>
          <span class="muted">Your Bid</span>
          <b>₹${num(data.proposed_bid)}</b>
        </div>
      </div>

      <hr>

      <h3>Route</h3>

      <div class="card soft">
        📍 ${esc(data.pickup_location)}
        <br><br>
        ↓
        <br><br>
        🏁 ${esc(data.delivery_location)}
      </div>

      <p>
        <b>Pickup:</b>
        ${esc(data.pickup_date)}
        ${esc(data.pickup_time || '')}
      </p>

      <p>
        <b>Instructions:</b>
        ${esc(data.special_instructions || 'None')}
      </p>

      <div class="alert">
        Your bid will be submitted as
        <strong>PENDING</strong>.
        A bid is not a confirmed transport booking until accepted.
      </div>

      <div class="actions">
        <button class="secondary"
          onclick="openRouteShareBid(${transporterId})">
          ← Edit
        </button>

        <button class="primary" onclick="submitRouteShareBid()">
          ✓ Confirm & Send Bid
        </button>
      </div>
    </div>
  `;
}

async function submitRouteShareBid() {
  try {
    if (!window.pendingRouteBid) {
      throw new Error('Route bid details are missing.');
    }

    const result = await api('/api/v2/v3/logistics-bids', {
      method: 'POST',
      body: JSON.stringify(window.pendingRouteBid)
    });

    window.pendingRouteBid = null;

    $('content').innerHTML = `
      <div class="card success-card">
        <div style="font-size:58px">✅</div>

        <h1>Route-Share Bid Submitted</h1>

        <p>
          Your transport bid has been recorded successfully.
        </p>

        <div class="card">
          <div class="grid3">
            <div>
              <span class="muted">Bid ID</span>
              <b>#${result.id}</b>
            </div>

            <div>
              <span class="muted">Status</span>
              <b>${esc(result.status)}</b>
            </div>

            <div>
              <span class="muted">Confirmation Code</span>
              <b>${esc(result.confirmation_code)}</b>
            </div>

            <div>
              <span class="muted">Transporter</span>
              <b>${esc(result.transporter_name)}</b>
            </div>

            <div>
              <span class="muted">Estimated Cost</span>
              <b>₹${num(result.estimated_cost)}</b>
            </div>

            <div>
              <span class="muted">Your Bid</span>
              <b>₹${num(result.proposed_bid)}</b>
            </div>
          </div>
        </div>

        <div class="alert">
          This is a bid acknowledgement, not yet a confirmed
          transport booking.
        </div>

        <div class="actions">
          <button class="primary"
            onclick="viewLogisticsBid(${result.id})">
            View Bid Details
          </button>

          <button class="secondary" onclick="buyerBulk()">
            Back to Logistics
          </button>
        </div>
      </div>
    `;
  } catch (e) {
    toast(e.message);
  }
}

async function viewLogisticsBid(bidId) {
  try {
    const b = await api(
      `/api/v2/v3/logistics-bids/${bidId}`
    );

    $('content').innerHTML = `
      <div class="hero">
        <div>
          <div class="eyebrow">
            LOGISTICS BID #${b.id}
          </div>

          <h1>${esc(b.transporter_name)}</h1>

          <p>
            Confirmation:
            ${esc(b.confirmation_code)}
          </p>
        </div>

        <span class="pill">
          ${esc(b.status)}
        </span>
      </div>

      <div class="card">
        <h2>Transport Details</h2>

        <div class="grid3">
          <div>
            <span class="muted">Vehicle</span>
            <b>${esc(b.vehicle_type || '—')}</b>
          </div>

          <div>
            <span class="muted">Vehicle No.</span>
            <b>${esc(b.vehicle_number || '—')}</b>
          </div>

          <div>
            <span class="muted">Rating</span>
            <b>⭐ ${num(b.rating)}</b>
          </div>

          <div>
            <span class="muted">Quantity</span>
            <b>${num(b.quantity_qtl)} qtl</b>
          </div>

          <div>
            <span class="muted">Reference Rate</span>
            <b>₹${num(b.rate_per_km)}/km</b>
          </div>

          <div>
            <span class="muted">Your Bid</span>
            <b>₹${num(b.proposed_bid)}</b>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>📍 Route</h2>

        <div class="card soft">
          <b>Pickup</b>
          <p>${esc(b.pickup_location)}</p>

          <div style="font-size:28px">↓</div>

          <b>Delivery</b>
          <p>${esc(b.delivery_location)}</p>
        </div>

        <p>
          <b>Date:</b>
          ${esc(b.pickup_date)}
          ${esc(b.pickup_time || '')}
        </p>

        <p>
          <b>Estimated distance:</b>
          ${num(b.estimated_distance_km)} km
        </p>

        <p>
          <b>Estimated reference cost:</b>
          ₹${num(b.estimated_cost)}
        </p>
      </div>

      <div class="card">
        <h2>Bid Status</h2>

        <span class="pill">
          ${esc(b.status)}
        </span>

        <p class="muted">
          PENDING means the bid has been submitted but transport
          is not yet confirmed.
        </p>
      </div>

      <button class="primary" onclick="buyerBulk()">
        ← Back to Bulk & Shared Logistics
      </button>
    `;
  } catch (e) {
    toast(e.message);
  }
}




// ADMIN
async function adminRoute(k){if(k==='dashboard')return adminDashboard();if(k==='usersKyc'||k==='securityActions')return adminUsers();if(k==='markets')return adminMarkets();if(k==='payments')return adminPayments();if(k==='grievances')return adminGrievances();if(k==='stateAnalytics')return adminAnalytics();if(k==='feedbackReq')return adminFeedback()}
async function adminDashboard(){let [d,risk,g]=await Promise.all([api('/api/v2/v3/dashboard'),api('/api/v2/risk-alerts'),api('/api/v2/grievances')]);$('content').innerHTML=`<div class="grid stats-4">${card(tr('revenue'),fmt(d.revenue),'Verified payment value','green')}${card(tr('sellers'),d.farmers,'Registered farmers')}${card(tr('buyers'),d.buyers,'Registered buyers')}${card(tr('pendingKyc'),d.pending_kyc,'Needs review')}${card(tr('grievances'),d.open_grievances,'Open cases')}${card(tr('risk'),risk.length,'Active risk alerts')}${card('Security','JWT + KYC + Webhooks','Role-based controls')}${card('Default','Tamil Nadu','Pan-India analytics')}</div>${section('Priority Grievances',g.slice(0,5).map(x=>`<div class="list-item"><div><b>#${x.id} ${esc(x.category)}</b><small>${esc(x.description)}</small></div><span class="severity ${String(x.severity).toLowerCase()}">${esc(x.severity)}</span></div>`).join('')||'<div class="empty">No open cases.</div>')}`}
async function adminUsers(){let users=await api('/api/v2/v3/admin/users');$('content').innerHTML=section(`${tr('usersKyc')} + Account Control`,`<div class="table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Location</th><th>KYC</th><th>Live</th><th>Account</th><th>Actions</th></tr></thead><tbody>${users.map(x=>`<tr><td><b>${esc(x.name)}</b><br><small>${esc(x.email)}</small></td><td>${esc(x.role)}</td><td>${esc(x.district)}, ${esc(x.state)}</td><td>${x.kyc_status==='VERIFIED'?'<span class="verified-badge">✓ Verified</span>':`<span class="tag">${esc(x.kyc_status||'Not started')}</span>`}<br><small>${esc(x.masked_document||'')}</small>${x.kyc_id&&x.kyc_status==='PENDING'?`<br><button class="secondary" onclick="adminVerifyKyc(${x.kyc_id})">Verify KYC</button>`:''}</td><td>${x.live_check?'✓':'—'}</td><td>${esc(x.account_action||'ACTIVE')}</td><td><div class="table-actions"><button onclick="adminAction(${x.id},'WARN')">Warn</button><button onclick="adminAction(${x.id},'BLOCK')">Block</button><button onclick="adminAction(${x.id},'UNBLOCK')">Unblock</button><button class="danger-btn" onclick="adminAction(${x.id},'TERMINATE')">Terminate</button><button onclick="adminMessage(${x.id})">Message</button></div></td></tr>`).join('')}</tbody></table></div>`)}

async function adminVerifyKyc(id){try{await api(`/api/v2/kyc/${id}`,{method:'PATCH',body:JSON.stringify({status:'VERIFIED',risk_note:'Live photo and masked KYC reviewed in SIH prototype'})});toast('KYC verified');adminUsers()}catch(e){toast(e.message)}}
async function adminAction(id,a){let reason=prompt(`${a} reason`,'Platform trust / grievance review');if(reason===null)return;try{await api(`/api/v2/v3/admin/users/${id}/action`,{method:'POST',body:JSON.stringify({action:a,reason})});toast(a);adminUsers()}catch(e){toast(e.message)}}
function adminMessage(id){let m=prompt('Admin message to user');if(!m)return;api(`/api/v2/v3/admin/users/${id}/message`,{method:'POST',body:JSON.stringify({message:m,severity:'warning'})}).then(()=>toast('Message sent')).catch(e=>toast(e.message))}
async function adminMarkets(){
  let [m,a,fs,bs]=await Promise.all([
    api(`/api/markets?state=${encodeURIComponent(currentState)}`),
    api(`/api/v2/v3/admin/state-analytics?state=${encodeURIComponent(currentState)}`),
    api(`/api/v2/v3/network?role=farmer&state=${encodeURIComponent(currentState)}`),
    api(`/api/v2/v3/network?role=buyer&state=${encodeURIComponent(currentState)}`)
  ]);
  $('content').innerHTML=`<div class="grid two">${section(`${tr('markets')} • ${currentState}`,m.map(x=>`<div class="list-item"><div><b>${esc(x.name)}</b><small>${esc(x.district)} • fee ${x.market_fee_pct}% • ${esc(x.facilities||'')}</small></div></div>`).join(''))}${section('Farmer / Buyer Market Activity',`<div class="grid stats-4">${card('Listings',a.listings)}${card('Upcoming harvests',a.harvests)}${card('Network farmers',a.farmers)}${card('Network buyers',a.buyers)}</div><canvas id="adminMarketChart"></canvas>`)}</div>${section('Farmer Details',`<div class="table-wrap"><table><thead><tr><th>Name</th><th>District</th><th>Crops</th><th>Volume</th><th>Rating</th></tr></thead><tbody>${fs.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.district)}</td><td>${esc(x.crops)}</td><td>${num(x.volume_qtl)} qtl</td><td>★ ${x.rating}</td></tr>`).join('')}</tbody></table></div>`)}${section('Buyer Details',`<div class="table-wrap"><table><thead><tr><th>Name</th><th>District</th><th>Crops</th><th>Demand volume</th><th>Rating</th></tr></thead><tbody>${bs.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.district)}</td><td>${esc(x.crops)}</td><td>${num(x.volume_qtl)} qtl</td><td>★ ${x.rating}</td></tr>`).join('')}</tbody></table></div>`)}`;
  charts.am=new Chart($('adminMarketChart'),{type:'bar',data:{labels:(a.crops||[]).map(x=>x.crop),datasets:[{label:'Listings',data:(a.crops||[]).map(x=>x.n)}]},options:{plugins:{legend:{display:false}}}})
}
async function adminPayments(){let p=await api('/api/v2/payments');$('content').innerHTML=section(tr('payments'),p.length?`<div class="table-wrap"><table><thead><tr><th>ID</th><th>User</th><th>Reference</th><th>Expected</th><th>Confirmed</th><th>Signature</th><th>Webhook</th><th>Status</th><th>Refund</th></tr></thead><tbody>${p.map(x=>`<tr><td>#${x.id}</td><td>${esc(x.user_name||x.user_id)}</td><td>${esc(x.reference_type)} #${x.reference_id}</td><td>${fmt(x.expected_amount_rupees)}</td><td>${fmt(x.confirmed_amount_rupees)}</td><td>${x.client_signature_verified?'✓':'—'}</td><td>${x.webhook_verified?'✓':'—'}</td><td>${esc(x.status)}</td><td>${x.refunds?.map(r=>`${fmt(r.amount_paise/100)} ${r.status}`).join(', ')||'—'}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">No payments yet.</div>')}
async function adminGrievances(){let [g,r]=await Promise.all([api('/api/v2/grievances'),api('/api/v2/risk-alerts')]);$('content').innerHTML=`${section('Grievance Resolution Monitor',g.map(x=>`<div class="grievance-card"><div><span class="severity ${String(x.severity).toLowerCase()}">${esc(x.severity)}</span><h3>#${x.id} • ${esc(x.category)} • ${esc(x.complainant_name||'User')}</h3><p>${esc(x.description)}</p><small>${esc(x.ai_recommendation||'')}</small></div><div><span class="tag">${esc(x.status)}</span><p>${x.status!=='RESOLVED'?'If unresolved or malicious behaviour is verified, use Users & KYC to warn/block/terminate the responsible account.':'Resolved'}</p></div></div>`).join('')||'<div class="empty">No grievances.</div>')}${section('Fraud / Risk Alerts',r.map(x=>`<div class="list-item"><div><b>${esc(x.risk_type)}</b><small>${esc(x.details)}</small></div><span class="severity ${x.score>75?'high':'medium'}">${x.score}</span></div>`).join('')||'<div class="empty">No alerts.</div>')}`}
async function adminAnalytics(){let a=await api(`/api/v2/v3/admin/state-analytics?state=${encodeURIComponent(currentState)}`);$('content').innerHTML=`<div class="grid stats-4">${card('Markets',a.markets)}${card('Listings',a.listings)}${card('Upcoming Harvests',a.harvests)}${card('Network Farmers',a.farmers)}${card('Network Buyers',a.buyers)}</div>${section(`${tr('stateAnalytics')} • ${currentState}`,`<canvas id="stateChart"></canvas><div class="table-wrap"><table><thead><tr><th>Crop</th><th>Listings</th><th>Avg price</th></tr></thead><tbody>${(a.crops||[]).map(x=>`<tr><td>${esc(x.crop)}</td><td>${x.n}</td><td>${fmt(x.avg_price)}</td></tr>`).join('')}</tbody></table></div>`)}`;charts.state=new Chart($('stateChart'),{type:'bar',data:{labels:['Markets','Listings','Harvests','Farmers','Buyers'],datasets:[{label:currentState,data:[a.markets,a.listings,a.harvests,a.farmers,a.buyers]}]},options:{plugins:{legend:{display:false}}}})}
async function adminFeedback(){let f=await api('/api/v2/feedback');$('content').innerHTML=section(tr('feedbackReq'),f.map(x=>`<div class="list-item"><div><b>${esc(x.category)} • ${esc(x.name||'User')}</b><small>★ ${x.rating} • ${esc(x.message)}</small></div>${button('Comment / Message',`adminMessage(${x.user_id})`)}</div>`).join('')||'<div class="empty">No feedback.</div>')}

function closeModal(){$('modal').classList.add('hidden')}
function voiceInto(id){let SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){toast('Voice recognition needs Chrome/Edge support.');return}let r=new SR();r.lang=(LANGS[currentLang]||LANGS.en)[1];r.interimResults=false;r.onstart=()=>toast(`🎙 ${LANGS[currentLang][0]}`);r.onresult=e=>{let el=$(id);if(el)el.value=(el.value?el.value+' ':'')+e.results[0][0].transcript};r.onerror=e=>toast(e.error);r.start()}

window.currentLang=currentLang;fillLangs();setLanguage(currentLang);selectRole(activeRole);if(token){api('/auth/me').then(x=>{me=x;boot()}).catch(()=>logout())}

/* Mobile navigation drawer. The sidebar overlays content below 900px, so it
   must close on navigation, on scrim tap and on Escape. */
function setNav(open){document.body.classList.toggle('nav-open',open);
 let sc=$('navScrim');if(sc)sc.classList.toggle('hidden',!open)}
function toggleNav(){setNav(!document.body.classList.contains('nav-open'))}
document.addEventListener('DOMContentLoaded',()=>{
 let t=$('navToggle');if(t)t.onclick=toggleNav;
 let sc=$('navScrim');if(sc)sc.onclick=()=>setNav(false);
 let nv=$('nav');if(nv)nv.addEventListener('click',e=>{if(e.target.closest('.nav-btn'))setNav(false)});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')setNav(false)});
 // A resize past the breakpoint must not leave the drawer state stuck on.
 addEventListener('resize',()=>{if(innerWidth>900)setNav(false)});
});
