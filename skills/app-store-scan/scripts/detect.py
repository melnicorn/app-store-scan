#!/usr/bin/env python3
"""Preflight for app-store-scan.

Profiles an Apple-platform project without spending model tokens on discovery:
platforms, Info.plist / entitlements / privacy manifest facts, dependencies,
grep "signals" with file:line evidence, deterministic hints, which review areas
apply, and what changed since each area was last scanned.

  detect.py <project>                 overview (areas to scan, changes since last scan)
  detect.py <project> --area a,b      evidence slice for just those areas

Every run rescans and rewrites <project>/.app-store-scan/profile.json.
"""
import argparse
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (AREAS, OUT_DIR, describe_git, git_log_between, git_state,  # noqa: E402
                    load_requirements, now, out_dir, read_json, write_json)

SKIP_DIRS = {'build', 'Build', 'DerivedData', 'Carthage', 'dist', 'target', 'out', 'coverage', 'venv',
             'android', 'windows', 'linux', 'web-build', '__pycache__', 'xcuserdata', 'vendor', 'logs', 'docs'}
SKIP_SUFFIX = ('.xcframework', '.framework', '.app', '.xcarchive', '.appex', '.bundle', '.dSYM', '.playground')
DEP_DIRS = {'Pods', 'node_modules', 'SourcePackages', 'checkouts', '.symlinks'}
CODE_EXT = {'.swift', '.m', '.mm', '.h', '.c', '.cc', '.cpp', '.rs', '.js', '.jsx', '.ts', '.tsx', '.dart',
            '.cs', '.vue', '.svelte', '.html'}
TEXT_EXT = {'.strings', '.xcstrings', '.storyboard', '.xib', '.stringsdict'}
MAX_BYTES = 1_500_000
ASSET_EXT = {'.ttf', '.otf', '.ttc', '.mp3', '.wav', '.m4a', '.caf', '.aiff', '.mp4', '.mov', '.mlmodel', '.mlpackage', '.usdz', '.csv', '.sqlite', '.db', '.geojson', '.gpx'}
LICENSE_RE = re.compile(r'^(LICEN[SC]E|COPYING|NOTICE|OFL|ACKNOWLEDG|THIRD[-_ ]?PARTY)', re.I)
TEST_RE = re.compile(r'(^|/)(tests?|__tests__|\w*Tests|spec|mocks?|fixtures?|e2e|examples?)(/|$)|\.(test|spec)\.', re.I)

# name, areas, regex, ignorecase, scope ('code' = source only, 'all' = source + UI strings)
SIGNALS = [  # noqa: E501
    # payments
    ('storekit', 'payments', r'\bimport StoreKit\b|SKPaymentQueue|SKProductsRequest|Product\.products\(|Transaction\.(currentEntitlements|updates)|SubscriptionStoreView|\bStoreView\(|react-native-iap|expo-in-app-purchases|in_app_purchase|RevenueCat|Purchases\.shared|react-native-purchases|purchases_flutter|\bAdapty\b|Qonversion|Glassfy|Superwall', 0, 'code'),
    ('restore_purchases', 'payments', r'restoreCompletedTransactions|AppStore\.sync\(|restorePurchases|restore_purchases|restore purchases?', 1, 'all'),
    ('external_payment', 'payments,macos', r'\bStripe\b|@stripe/|stripe-react-native|flutter_stripe|\bPayPal\b|Braintree|\bPaddle\b|Razorpay|\bAdyen\b|LemonSqueezy|Gumroad|FastSpring|\bKlarna\b|SquareInAppPayments|checkout\.com', 0, 'code'),
    ('apple_pay', 'payments', r'PKPaymentAuthorization|PKPaymentRequest|PKPaymentButton|PayWithApplePayButton', 0, 'code'),
    ('paywall_copy', 'payments', r'\bsubscri(be|ption)s?\b|free trial|\bpaywall\b|\bpremium\b|\bupgrade to\b|\bunlock\b|go pro\b|per (month|year|week)|/ ?(mo|yr)\b', 1, 'all'),
    ('external_purchase_link', 'payments', r'ExternalPurchase|ExternalLinkAccount|external-purchase|buy (it )?on (our|the) (web)?site|cheaper on', 1, 'all'),
    ('license_key', 'payments,macos', r'licen[sc]e ?key|serial ?number|activation ?(code|key)|redeem ?code|unlock ?code|promo ?code', 1, 'all'),
    ('loot_box', 'payments', r'loot ?box|\bgacha\b|mystery (box|crate|pack)|random (reward|item|drop)', 1, 'all'),
    ('virtual_currency', 'payments', r'\b(coins?|gems?|credits?|tokens?)Balance\b|buy ?(coins|gems|credits|tokens)|in-?game currency', 1, 'all'),
    ('tipping', 'payments', r'\btip ?jar\b|buy me a coffee|ko-fi|patreon|\bdonat(e|ion)s?\b', 1, 'all'),
    # accounts
    ('login', 'accounts', r'signInWith|\bsignIn\(|\blogin\(|LoginView|LoginScreen|SignInView|SignInScreen|Auth\.auth\(\)|supabase\.auth|FirebaseAuth|firebase_auth|Amplify\.Auth|\bCognito|Auth0|ASWebAuthenticationSession|\bClerk\b|passwordField|SecureField\(', 0, 'code'),
    ('third_party_login', 'accounts', r'GoogleSignIn|GIDSignIn|FBSDKLoginKit|FacebookLogin|react-native-fbsdk|google-signin|google_sign_in|flutter_facebook_auth|TwitterLogin|LinkedIn(Login|SDK)|\bWXApi\b|WeChatLogin|LoginWithAmazon|signInWithOAuth|provider: *[\'"](google|facebook|twitter|github|linkedin|discord)|(Google|Facebook|Twitter|GitHub)AuthProvider', 0, 'code'),
    ('sign_in_with_apple', 'accounts', r'ASAuthorizationAppleID|SignInWithAppleButton|AppleAuthentication|apple-authentication|sign_in_with_apple|appleAuth\b|apple\.com["\']|provider: *[\'"]apple', 0, 'code'),
    ('account_creation', 'accounts', r'sign ?up\b|create ?(an )?account|createUser|register(User|Account)|createUserWithEmail|\bregistration\b', 1, 'all'),
    ('account_deletion', 'accounts', r'delete ?(my |your )?account|deleteAccount|deleteUser|account ?deletion|user\.delete\(|remove ?account|close ?account', 1, 'all'),
    ('face_auth', 'accounts', r'\bLAContext\b|LocalAuthentication|local_auth|expo-local-authentication|ARFaceTrackingConfiguration', 0, 'code'),
    # permissions (API use -> purpose string)
    ('camera', 'permissions', r'AVCaptureDevice|AVCaptureSession|\.camera\b.*sourceType|sourceType *= *\.camera|expo-camera|vision-camera|react-native-camera|DataScannerViewController|VNDocumentCameraViewController', 0, 'code'),
    ('microphone', 'permissions', r'AVAudioRecorder|requestRecordPermission|AVAudioApplication\.requestRecordPermission|inputNode\.installTap|expo-av|react-native-audio-record|\bSFSpeechRecognizer\b', 0, 'code'),
    ('speech', 'permissions', r'SFSpeechRecognizer|SpeechAnalyzer|SpeechTranscriber', 0, 'code'),
    ('location', 'permissions', r'CLLocationManager|requestWhenInUseAuthorization|requestAlwaysAuthorization|CLLocationUpdate|expo-location|\bgeolocator\b|react-native-geolocation|navigator\.geolocation', 0, 'code'),
    ('location_always', 'permissions', r'requestAlwaysAuthorization|allowsBackgroundLocationUpdates|startMonitoringSignificantLocationChanges', 0, 'code'),
    ('photos_full', 'permissions', r'PHPhotoLibrary\.(requestAuthorization|shared)|PHAsset\.fetchAssets|expo-media-library|photo_manager|UIImageWriteToSavedPhotosAlbum', 0, 'code'),
    ('photos_picker', 'permissions', r'PHPickerViewController|\bPhotosPicker\(|UIImagePickerController|expo-image-picker|image_picker', 0, 'code'),
    ('contacts', 'permissions,privacy', r'CNContactStore|ContactAccessButton|expo-contacts|react-native-contacts|flutter_contacts|contacts_service', 0, 'code'),
    ('contacts_picker', 'permissions', r'CNContactPickerViewController', 0, 'code'),
    ('calendar', 'permissions', r'\bEKEventStore\b', 0, 'code'),
    ('bluetooth', 'permissions', r'CBCentralManager|CBPeripheralManager|react-native-ble|flutter_blue', 0, 'code'),
    ('motion', 'permissions', r'CMMotionActivityManager|CMPedometer|CMAltimeter|CMMotionManager', 0, 'code'),
    ('local_network', 'permissions', r'\bNWBrowser\b|\bNWListener\b|NetServiceBrowser|MCNearbyServiceBrowser|MultipeerConnectivity|NWConnection\b|\bUdpSocket\b', 0, 'code'),
    ('nfc', 'permissions', r'NFCNDEFReaderSession|NFCTagReaderSession', 0, 'code'),
    ('healthkit', 'permissions,health', r'HKHealthStore|import HealthKit|react-native-health|\bhealth_kit\b|HKClinical|\bCareKit\b|ResearchKit|HKWorkout', 0, 'code'),
    ('homekit', 'permissions,technical', r'HMHomeManager|import HomeKit', 0, 'code'),
    ('musickit', 'permissions,design', r'import MusicKit|MPMusicPlayerController|SKCloudServiceController|MPMediaLibrary|MusicAuthorization', 0, 'code'),
    ('att', 'permissions', r'ATTrackingManager|requestTrackingAuthorization|tracking-transparency|app_tracking_transparency', 0, 'code'),
    ('idfa', 'permissions,privacy', r'advertisingIdentifier|ASIdentifierManager|\bIDFA\b', 0, 'code'),
    ('ads_sdk', 'permissions,design,kids', r'GoogleMobileAds|GADBannerView|GADInterstitial|google-mobile-ads|google_mobile_ads|\bAdMob\b|AppLovin|IronSource|UnityAds|FBAudienceNetwork|AdColony|\bVungle|Chartboost|\bInMobi|MoPub|\bPangle|Mintegral|SKAdNetwork|AdServices', 0, 'code'),
    ('analytics_sdk', 'permissions,privacy,kids', r'FirebaseAnalytics|Analytics\.logEvent|\bAmplitude\b|\bMixpanel\b|AppsFlyer|\bAdjust(SDK)?\b|BranchSDK|\bSentry\b|Crashlytics|\bPostHog\b|\bFlurry\b|\bBugsnag\b|Datadog|NewRelic|\bSingular\b|\bKochava\b|\bOneSignal\b|\bBraze\b|CleverTap|\bIntercom\b|TelemetryDeck|\bAptabase\b|segment\.(com|io)|@segment/', 0, 'code'),
    ('session_replay', 'permissions,privacy', r'FullStory|LogRocket|Smartlook|\bUXCam\b|Glassbox|\bHotjar\b|sessionReplay|session_replay|Clarity', 0, 'code'),
    ('screen_recording', 'permissions', r'RPScreenRecorder|import ReplayKit|\bSCStream\b|ScreenCaptureKit|CGWindowListCreateImage|CGDisplayStream', 0, 'code'),
    ('permission_gate', 'permissions', r'(must|need to|have to|required to|please) (enable|allow|turn on|grant) (push |local )?(notifications?|location|tracking|camera|contacts|microphone)|to continue,? (enable|allow)', 1, 'all'),
    ('rr_userdefaults', 'permissions', r'\bUserDefaults\b|NSUserDefaults|@AppStorage|AsyncStorage|shared_preferences|SharedPreferences', 0, 'code'),
    ('rr_file_timestamp', 'permissions', r'creationDate\b|modificationDate\b|contentModificationDateKey|creationDateKey|fileModificationDate|\b[fl]?stat\(\s*[\w.\[\]]+\s*,\s*&|getattrlist|NSFileModificationDate|NSFileCreationDate|fs::(symlink_)?metadata\(|\.metadata\(\)|\.modified\(\)|\.created\(\)', 0, 'code'),
    ('rr_boot_time', 'permissions', r'systemUptime|mach_absolute_time|kern\.boottime', 0, 'code'),
    ('rr_disk_space', 'permissions', r'volumeAvailableCapacity|systemFreeSize|systemSize\b|\bstatv?fs\(|NSFileSystemFreeSize|NSFileSystemSize', 0, 'code'),
    ('rr_keyboards', 'permissions', r'activeInputModes', 0, 'code'),
    ('secrets', 'permissions', r'sk_live_[0-9a-zA-Z]{10,}|\bsk-[A-Za-z0-9_\-]{24,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{35}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|xox[baprs]-[0-9A-Za-z-]{10,}|ghp_[0-9A-Za-z]{36}', 0, 'code'),
    # privacy
    ('third_party_ai', 'privacy,ugc', r'api\.openai\.com|\bopenai\b|anthropic|generativelanguage\.googleapis|GoogleGenerativeAI|\bgemini-|mistral\.ai|\bcohere\b|replicate\.com|huggingface|elevenlabs|stability\.ai|\bgroq\b|perplexity|deepseek|openrouter|chat/completions|\bclaude-', 1, 'code'),
    ('network_calls', 'privacy', r'\bNWConnection\b|\bNWBrowser\b|\bsocket\(|\bsendto\(|\brecvfrom\(|UdpSocket|TcpStream|URLSession|\bAlamofire\b|\bfetch\(|\baxios\b|http\.(get|post)\(|\bDio\(|reqwest|URLRequest\(', 0, 'code'),
    ('installed_apps', 'privacy', r'canOpenURL|LSApplicationWorkspace', 0, 'code'),
    ('insecure_storage', 'privacy', r'(UserDefaults|AsyncStorage|SharedPreferences|@AppStorage)[^\n]{0,80}(token|password|secret|apiKey|credential)|(token|password|secret)[^\n]{0,40}UserDefaults', 1, 'code'),
    ('privacy_policy_link', 'privacy', r'privacy[ _-]?policy|/privacy\b|terms (of (use|service))|\bEULA\b', 1, 'all'),
    # technical
    ('uiwebview', 'technical', r'\bUIWebView\b', 0, 'code'),
    ('webview', 'technical,design', r'WKWebView|react-native-webview|webview_flutter|InAppWebView|SFSafariViewController|\bWebView\(', 0, 'code'),
    ('private_api', 'technical', r'NSSelectorFromString|NSClassFromString|performSelector|\bdlsym\(|\bdlopen\(|PrivateFrameworks|value\(forKey: *"_|valueForKey:@"_|setValue\([^)\n]*forKey: *"_|LSApplicationWorkspace|method_exchangeImplementations|objc_msgSend|@_silgen_name', 0, 'code'),
    ('dynamic_code', 'technical', r'CodePush|code-push|expo-updates|JSPatch|\bshorebird\b|hot ?update|react-native-ota|\bJSContext\b|JSVirtualMachine|\bnew Function\(|[^.\w]eval\(|downloadAndRun|remote ?bundle|\bwasm\b', 1, 'code'),
    ('ipv4_only', 'technical', r'\bAF_INET\b(?!6)|gethostbyname\(|inet_addr\(|inet_aton\(|\bsockaddr_in\b(?!6)|Ipv4Addr|SocketAddrV4|["\']\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?["\'/]', 0, 'code'),
    ('insecure_http', 'technical,permissions', r'["\']http://(?!localhost|127\.0\.0\.1|www\.w3\.org|www\.apple\.com/DTDs|schemas\.|ns\.adobe|purl\.org|xmlpull|[^"\']*\.local\b)[^"\']+', 0, 'code'),
    ('hidden_features', 'technical', r'RemoteConfig|remote_config|feature ?flags?|kill ?switch|isAppReview|inReview|isReviewer|reviewMode|hidden ?feature|LaunchDarkly|\bStatsig\b|Optimizely|GrowthBook|ConfigCat|secret ?(menu|tap|gesture|code)|easter ?egg|debug ?menu', 1, 'code'),
    ('mining', 'technical', r'coinhive|cryptonight|xmrig|stratum\+tcp', 1, 'code'),
    ('system_prompts', 'technical', r'restart your (device|iphone|ipad|mac)|turn off (wi-?fi|bluetooth)|disable [^"\n]{0,30}(security|firewall|gatekeeper|passcode)|App-Prefs:|prefs:root', 1, 'all'),
    ('background_work', 'technical', r'BGTaskScheduler|beginBackgroundTask|allowsBackgroundLocationUpdates|PKPushRegistry|AVAudioSession[^\n]*\.playback', 0, 'code'),
    ('matter', 'technical', r'MatterSupport|\bMTRDevice|import Matter\b', 0, 'code'),
    ('file_browsing', 'technical', r'UIDocumentPickerViewController|\.fileImporter\(|UIDocumentBrowserViewController|FileManager\.default\.contentsOfDirectory', 0, 'code'),
    ('arkit', 'technical,design', r'import ARKit|\bARSession\b|\bARView\b|ARSCNView|import RealityKit', 0, 'code'),
    # completeness
    ('placeholder', 'completeness', r'lorem ipsum|coming soon|under construction|placeholder text|your (text|title|description) here|\bexample\.(com|org)\b|test@test|foo@bar|sample text|not (yet )?implemented|\bTBD\b', 1, 'all'),
    ('beta_wording', 'completeness', r'["\'>][^"\'<\n]{0,60}\b(beta|demo version|trial version|preview build|test build|alpha version|early access)\b', 1, 'all'),
    ('dev_endpoints', 'completeness', r'["\'](https?|wss?)://(localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\.|[^"\']*(staging|\.ngrok|dev\.|-dev\b|\.test\b|sandbox))', 1, 'code'),
    ('crash_risk', 'completeness', r'fatalError\(|\btry!|as! |unimplemented!?\(|todo!\(|preconditionFailure\(|\.unwrap\(\)|\.expect\(|panic!\(', 0, 'code'),
    ('custom_crypto', 'completeness', r'salsa20|chacha20|\bAES\b|CCCrypt|import CryptoKit|CommonCrypto|libsodium|\bopenssl\b|ed25519|\bRSA\b|x25519|\bcipher\b', 1, 'code'),
    ('app_entry', 'design,completeness', r'^@main\b|@UIApplicationMain|AppRegistry\.registerComponent|\brunApp\(|WindowGroup\s*\{', 0, 'code'),
    ('empty_states', 'design,completeness', r'ContentUnavailableView|no (connection|data|results|devices?)\b|not connected|waiting for|searching for|demo ?mode|sample data|simulat(e|ed|or|ion)\b|replay', 1, 'all'),
    ('support_link', 'metadata,design', r'mailto:|support@|/support\b|contact (us|support)|send feedback|help ?center|about ?view|AboutView|acknowledg', 1, 'all'),
    ('debug_only', 'completeness', r'#if DEBUG|__DEV__|kDebugMode|isDebugBuild', 0, 'code'),
    # metadata / content
    ('other_platforms', 'metadata', r'["\'`>][^"\'`<\n]{0,80}(Google Play|Play Store|Galaxy Store|AppGallery|Amazon Appstore|available on Android|Android (app|version|phone|device)|for Android|Windows Phone|\bAltStore\b)', 1, 'all'),
    ('apple_terms', 'content', r'["\'>][^"\'<\n]{0,80}(endorsed by Apple|approved by Apple|Apple recommends|Editor.?s Choice|App of the Day|official Apple)', 1, 'all'),
    ('third_party_brands', 'content', r'\b(PlayStation|Xbox|Nintendo|Netflix|Spotify|YouTube|Instagram|TikTok|Facebook|Disney|Marvel|Pok[eé]mon|Gran Turismo|FIFA|NFL|NBA|Tesla|WhatsApp|Snapchat|Twitter|Minecraft|Fortnite)\b', 0, 'all'),
    ('media_download', 'content', r'youtube-?dl|yt-?dlp|\bytdl\b|XCDYouTubeKit|youtubei|download(Video|Audio)[^\n]{0,40}(youtube|soundcloud|vimeo|tiktok)', 1, 'code'),
    ('apple_sites', 'design', r'itunes\.apple\.com/(search|lookup|[a-z]{2}/rss)|rss\.applemarketingtools|appstoreconnect\.apple\.com|scrape', 1, 'code'),
    ('objectionable', 'content', r'\bnsfw\b|\bporn|\bxxx\b|adult content|\bnude|hookup|prank call|fake (call|location|gps)|anonymous (call|sms|text)', 1, 'all'),
    ('substances', 'content,regulated', r'\bvap(e|ing)\b|tobacco|cigarette|cannabis|marijuana|dispensary|firearm|ammunition|\bcbd\b|drinking game', 1, 'all'),
    # design
    ('review_prompt_api', 'design', r'SKStoreReviewController|requestReview|in_app_review|react-native-in-app-review|expo-store-review', 0, 'code'),
    ('custom_review_prompt', 'design', r'rate (us|this app|the app|our app)|leave (us )?a review|write a review|5[- ]stars?\b|five[- ]stars?|action=write-review|enjoying [^"\n]{0,30}\?', 1, 'all'),
    ('forced_actions', 'design', r'(rate|review|share|invite|follow)[^"\n]{0,40}to (unlock|continue|access)|download [^"\n]{0,30}to (unlock|continue)', 1, 'all'),
    ('push', 'design', r'UNUserNotificationCenter|registerForRemoteNotifications|FirebaseMessaging|expo-notifications|firebase_messaging|\bOneSignal\b', 0, 'code'),
    ('game_center', 'design', r'GKLocalPlayer|import GameKit|GKLeaderboard', 0, 'code'),
    ('geo_restriction', 'design', r'CTCarrier|carrierName|isoCountryCode|Locale\.current\.region|not available in your (country|region)', 1, 'code'),
    ('interstitial_ads', 'design', r'Interstitial|RewardedAd|AppOpenAd|rewarded_ad', 0, 'code'),
    # ugc
    ('ugc', 'ugc', r'createPost|addComment|sendMessage|upload(Photo|Video|Image|Avatar)|PostView|CommentView|ChatView|FeedView|ChatScreen|FeedScreen|PostScreen|CommentScreen|user[-_ ]?generated|StreamChat|Sendbird|getstream|TalkJS|PubNub|\bAgora\b|Twilio(Chat|Video|Conversations)|LiveKit|shareToCommunity|publicProfile', 0, 'code'),
    ('moderation', 'ugc', r'report(User|Post|Content|Comment|Abuse|Message)|blockUser|block_user|flag(Content|Post|User)|reportReason|\bmoderation\b|profanity|objectionable|report (this|user|post|content|abuse)|block (this )?user', 1, 'all'),
    ('ai_generation', 'ugc', r'image generation|generateImage|text-to-image|dall-?e|stable.?diffusion|midjourney|chat ?bot|ImagePlayground|FoundationModels|LanguageModelSession|ai[- ]generated', 1, 'code'),
    ('anonymous_chat', 'ugc', r'anonymous (chat|message|post)|random (chat|match|stranger)|hot ?or ?not', 1, 'all'),
    ('mini_apps', 'ugc', r'mini ?(app|game|program)s?\b|\bemulator\b|\bROMs?\b|plug-?in ?(store|marketplace)|cloud gaming|game streaming', 1, 'all'),
    # kids
    ('kids', 'kids', r'\bfor kids\b|\bkids?[\'’]?s? (app|mode|category|game|zone)|toddler|preschool|kindergarten|\bCOPPA\b|parental ?gate|made for kids|child(ren)?[\'’]s (app|game|learning)|DeclaredAgeRange|AgeRangeService|ask a grown-?up', 1, 'all'),
    ('age_gate', 'kids,ugc', r'date ?of ?birth|birth ?(date|day|year)|age ?(gate|verification|check)|\b(over|under) ?(13|16|17|18|21)\b|\b(13|17|18|21)\+', 1, 'all'),
    # health
    ('medical_claims', 'health', r'blood (pressure|glucose|sugar|oxygen)|\bSpO2\b|body temperature|diagnos(e|is|tic)|\bdosage\b|\bdose\b|symptom|medication|\bECG\b|\bEKG\b|medical (advice|device)|clinical|x-?ray', 1, 'all'),
    # regulated
    ('gambling', 'regulated', r'\bcasino\b|\bbetting\b|sportsbook|\bpoker\b|slot machine|\blottery\b|\braffle\b|sweepstakes|\bwager|real[- ]money|card counter|\bbingo\b', 1, 'all'),
    ('vpn', 'regulated', r'NEVPNManager|NETunnelProvider|NEPacketTunnel|NEAppProxy|NEDNSProxy|NEFilter|import NetworkExtension|WireGuard|OpenVPN', 0, 'code'),
    ('mdm', 'regulated', r'ManagedSettings|DeviceActivity|FamilyControls|\.mobileconfig|com\.apple\.configuration\.managed|\bMDM\b', 0, 'code'),
    ('crypto', 'regulated,payments', r'walletconnect|\bweb3\b|\bethers\b|bitcoin|ethereum|\bsolana\b|\bNFTs?\b|cryptocurrenc|metamask|\bblockchain\b|seed ?phrase|\bICO\b', 1, 'all'),
    ('finance', 'regulated', r'\bAPR\b|payday|personal loan|loan (amount|term|offer)|stock trading|brokerage|\bforex\b|\bCFDs?\b|binary options|\binsurance (policy|quote|premium)|\bcharity\b|fundrais', 1, 'all'),
    ('crime_reporting', 'regulated', r'report (a )?crime|DUI checkpoint|sobriety checkpoint', 1, 'all'),
    # extensions
    ('siri_intents', 'extensions', r'\bINIntent\b|import Intents\b|AppShortcutsProvider|import AppIntents|: AppIntent\b|INInteraction', 0, 'code'),
    ('widgets', 'extensions', r'import WidgetKit|import ActivityKit|WidgetConfiguration|ActivityAttributes', 0, 'code'),
    ('callkit', 'extensions', r'CXProvider|CXCallDirectory|import CallKit|ILMessageFilter|IdentityLookup', 0, 'code'),
    ('keyboard_ext', 'extensions', r'UIInputViewController|RequestsOpenAccess', 0, 'code'),
    # macOS
    ('mac_updater', 'macos', r'\bSparkle\b|SUUpdater|SPUUpdater|SPUStandardUpdaterController|SUFeedURL|\bSquirrel\b|electron-updater|autoUpdater|appcast|tauri-plugin-updater|checkForUpdates', 0, 'code'),
    ('mac_login_item', 'macos', r'SMLoginItemSetEnabled|SMAppService|LSSharedFileList|LaunchAgents|LaunchDaemons|launchctl|openAtLogin|setLoginItemSettings|auto-launch|launch at login', 1, 'all'),
    ('mac_privileged', 'macos', r'AuthorizationExecuteWithPrivileges|SMJobBless|AuthorizationCreate|\bsudo\b|\bsetuid\b|with administrator privileges|SMAppService\.daemon|PrivilegedHelper', 0, 'code'),
    ('mac_process', 'macos', r'\bProcess\(\)|\bNSTask\b|posix_spawn|[^.\w]system\(|\bpopen\(|child_process|NSAppleScript|OSAScript|/bin/(ba|z)?sh\b|Command::new', 0, 'code'),
    ('mac_installs_code', 'macos', r'\.pkg["\']|\.dmg["\']|installer -pkg|kextload|\.kext\b|OSSystemExtensionRequest|pip3? install|npm install|brew install|curl [^\n]*\| *(ba)?sh', 0, 'code'),
    ('mac_file_access', 'macos', r'NSHomeDirectory\(\)|homeDirectoryForCurrentUser|["\']~/|["\']/(Library|usr/local|Applications|Users|private|etc|opt)/|NSOpenPanel|NSSavePanel|startAccessingSecurityScopedResource|bookmarkData', 0, 'code'),
    ('mac_dock_desktop', 'macos', r'/Desktop\b|addToDock|dockutil|com\.apple\.dock|persistent-apps', 0, 'code'),
    ('mac_deprecated', 'macos', r'\bJavaVM\b|JavaAppletPlugin|\bQTKit\b|import Carbon|NSOpenGL|/usr/bin/python|Python\.framework|\bWebView\b[^(]|x86_64', 0, 'code'),
    ('mac_tcc', 'macos', r'AXIsProcessTrusted|CGEvent\.tapCreate|CGEventTapCreate|IOHIDManager|kTCCService|tccutil|NSAppleEventsUsageDescription|CGRequestScreenCaptureAccess', 0, 'code'),
]

# signal -> purpose-string keys, any one of which satisfies it
PURPOSE = {
    'camera': ['NSCameraUsageDescription'],
    'microphone': ['NSMicrophoneUsageDescription'],
    'speech': ['NSSpeechRecognitionUsageDescription'],
    'location': ['NSLocationWhenInUseUsageDescription', 'NSLocationAlwaysAndWhenInUseUsageDescription', 'NSLocationUsageDescription'],
    'photos_full': ['NSPhotoLibraryUsageDescription', 'NSPhotoLibraryAddUsageDescription'],
    'contacts': ['NSContactsUsageDescription'],
    'calendar': ['NSCalendarsUsageDescription', 'NSCalendarsFullAccessUsageDescription', 'NSCalendarsWriteOnlyAccessUsageDescription'],
    'bluetooth': ['NSBluetoothAlwaysUsageDescription'],
    'motion': ['NSMotionUsageDescription'],
    'nfc': ['NFCReaderUsageDescription'],
    'healthkit': ['NSHealthShareUsageDescription', 'NSHealthUpdateUsageDescription'],
    'homekit': ['NSHomeKitUsageDescription'],
    'musickit': ['NSAppleMusicUsageDescription'],
    'att': ['NSUserTrackingUsageDescription'],
    'face_auth': ['NSFaceIDUsageDescription'],
}
RR_CATEGORY = {
    'rr_userdefaults': 'NSPrivacyAccessedAPICategoryUserDefaults',
    'rr_file_timestamp': 'NSPrivacyAccessedAPICategoryFileTimestamp',
    'rr_boot_time': 'NSPrivacyAccessedAPICategorySystemBootTime',
    'rr_disk_space': 'NSPrivacyAccessedAPICategoryDiskSpace',
    'rr_keyboards': 'NSPrivacyAccessedAPICategoryActiveKeyboards',
}
PLIST_KEYS = ['UIAppFonts', 'CFBundleDisplayName', 'CFBundleName', 'CFBundleShortVersionString', 'CFBundleVersion',
              'UIBackgroundModes', 'NSAppTransportSecurity', 'ITSAppUsesNonExemptEncryption',
              'LSApplicationQueriesSchemes', 'UIRequiredDeviceCapabilities', 'LSMinimumSystemVersion',
              'MinimumOSVersion', 'UILaunchStoryboardName', 'UILaunchScreen', 'UIRequiresFullScreen',
              'LSUIElement', 'SUFeedURL', 'UIFileSharingEnabled', 'LSSupportsOpeningDocumentsInPlace',
              'BGTaskSchedulerPermittedIdentifiers', 'NSBonjourServices', 'LSApplicationCategoryType',
              'NSUserActivityTypes', 'UISupportedInterfaceOrientations', 'UISupportedInterfaceOrientations~ipad',
              'CFBundleURLTypes', 'UIApplicationSceneManifest', 'NSExtension', 'WKApplication', 'UIDeviceFamily']
PRODUCT_TYPES = {
    'com.apple.product-type.application': 'app',
    'com.apple.product-type.app-extension': 'extension',
    'com.apple.product-type.extensionkit-extension': 'extension',
    'com.apple.product-type.application.on-demand-install-capable': 'app-clip',
    'com.apple.product-type.application.watchapp2': 'watch-app',
    'com.apple.product-type.watchkit2-extension': 'watch-extension',
    'com.apple.product-type.application.messages': 'imessage-app',
    'com.apple.product-type.app-extension.messages-sticker-pack': 'sticker-pack',
    'com.apple.product-type.xpc-service': 'xpc-service',
    'com.apple.product-type.system-extension': 'system-extension',
    'com.apple.product-type.driver-extension': 'driver-extension',
}
SDK_PLATFORM = {'iphoneos': 'ios', 'iphonesimulator': 'ios', 'macosx': 'macos', 'appletvos': 'tvos',
                'appletvsimulator': 'tvos', 'watchos': 'watchos', 'watchsimulator': 'watchos',
                'xros': 'visionos', 'xrsimulator': 'visionos'}


def read_text(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, 'rb') as f:
            b = f.read()
        if b[:2] in (b'\xff\xfe', b'\xfe\xff'):
            return b.decode('utf-16', 'replace')
        return b.decode('utf-8', 'replace')
    except OSError:
        return None


def vtuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:3]) or (0,)


def load_plist(path):
    try:
        with open(path, 'rb') as f:
            d = plistlib.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        t = read_text(path) or ''
        return {k: v for k, v in re.findall(r'<key>(\w+)</key>\s*<string>(.*?)</string>', t, re.S)}


def simple(v, depth=0):
    """JSON-safe, size-bounded copy of a plist value."""
    if isinstance(v, dict):
        return {str(k): simple(x, depth + 1) for k, x in list(v.items())[:40]} if depth < 4 else '{...}'
    if isinstance(v, (list, tuple)):
        return [simple(x, depth + 1) for x in v[:40]]
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


class Scan:
    def __init__(self, root, max_hits, exclude=()):
        self.root = os.path.abspath(root)
        self.exclude = tuple(e.strip('/') for e in exclude)
        self.max_hits = max_hits
        self.req = load_requirements()
        self.sig = {n: {'count': 0, 'files': 0, 'hits': []} for n, *_ in SIGNALS}
        self.compiled = [(n, re.compile(p, re.I if ic else 0), scope) for n, _a, p, ic, scope in SIGNALS]
        self.tree = {}
        self.types = set()
        self.platforms = set()
        self.xcodeprojs = []
        self.build = {}
        self.targets = []
        self.plists = {}
        self.usage = {}
        self.entitlements = {}
        self.manifests = {}
        self.sdk_manifests = set()
        self.dep_dirs_seen = False
        self.deps = set()
        self.icons = []
        self.metadata = {}
        self.notes = []
        self.code_files = 0
        self.assets = []
        self.licenses = []

    def rel(self, p):
        return os.path.relpath(p, self.root)

    # ---- walking -------------------------------------------------------
    def run(self):
        for dp, dns, fns in os.walk(self.root):
            keep = []
            for d in dns:
                full = os.path.join(dp, d)
                if self.rel(full) in self.exclude:
                    continue
                if d in DEP_DIRS:
                    self.dep_dirs_seen = True
                    self.scan_dep_dir(full)
                elif d.endswith('.xcodeproj'):
                    self.xcodeprojs.append(self.rel(full))
                    self.parse_pbx(os.path.join(full, 'project.pbxproj'))
                elif d.endswith('.appiconset'):
                    self.check_icon(full)
                elif d == 'metadata' and os.path.basename(dp) == 'fastlane':
                    self.parse_metadata(full)
                elif d in SKIP_DIRS or d.endswith(SKIP_SUFFIX) or (d.startswith('.') and d != '.github'):
                    continue
                else:
                    keep.append(d)
            dns[:] = keep
            for fn in fns:
                self.visit(os.path.join(dp, fn), fn)
        self.finish()

    def visit(self, path, fn):
        rel = self.rel(path)
        ext = os.path.splitext(fn)[1].lower()
        if ext in ASSET_EXT and len(self.assets) < 60:
            self.assets.append(rel)
        if LICENSE_RE.match(fn):
            self.licenses.append(rel)
        handler = None
        if fn.endswith('Info.plist'):
            handler = self.parse_info_plist
        elif ext == '.entitlements':
            handler = self.parse_entitlements
        elif fn == 'PrivacyInfo.xcprivacy':
            handler = self.parse_manifest
        elif fn in ('Podfile.lock', 'Package.resolved', 'Package.swift', 'Cartfile', 'Cartfile.resolved',
                    'package.json', 'pubspec.yaml', 'app.json', 'app.config.js', 'app.config.ts', 'project.yml',
                    'capacitor.config.json', 'capacitor.config.ts', 'config.xml', 'tauri.conf.json',
                    'electron-builder.yml', 'electron-builder.json', 'Cargo.toml', 'Podfile'):
            handler = self.parse_config
        if ext in CODE_EXT or ext in TEXT_EXT or handler:
            text = read_text(path)
            if text is None:
                return
            self.tree[rel] = hashlib.sha1(text.encode('utf-8', 'replace')).hexdigest()[:12]
            if handler:
                handler(path, rel, text)
            if ext == '.rs' and '#[cfg(test)]' in text:
                text = text[:text.index('#[cfg(test)]')]
            if (ext in CODE_EXT or ext in TEXT_EXT) and not fn.endswith('.min.js') and not TEST_RE.search(rel):
                self.code_files += ext in CODE_EXT
                self.grep(rel, text, 'code' if ext in CODE_EXT else 'text')

    def grep(self, rel, text, kind):
        for name, rx, scope in self.compiled:
            if kind == 'text' and scope == 'code':
                continue
            s = self.sig[name]
            n = shown = 0
            for m in rx.finditer(text):
                n += 1
                if len(s['hits']) < self.max_hits and shown < 3:
                    line = text.count('\n', 0, m.start()) + 1
                    a = text.rfind('\n', 0, m.start()) + 1
                    b = text.find('\n', m.end())
                    snippet = text[a:b if b != -1 else len(text)].strip()[:140]
                    if snippet.startswith(('//', '#', '*', '/*', '<!--')) and name != 'placeholder':
                        continue  # counted, but a comment is poor evidence
                    shown += 1
                    if name == 'secrets':
                        snippet = '[value redacted]'
                    s['hits'].append({'file': rel, 'line': line, 'text': snippet})
                if n >= 50:
                    break
            if n:
                s['count'] += n
                s['files'] += 1

    def scan_dep_dir(self, d):
        base = d.count(os.sep)
        for dp, dns, fns in os.walk(d):
            depth = dp.count(os.sep) - base
            dns[:] = [x for x in dns if depth < 5 and x not in ('node_modules', '.git', 'android')]
            if 'PrivacyInfo.xcprivacy' in fns:
                parts = os.path.relpath(dp, d).split(os.sep)
                pkg = '/'.join(parts[:2]) if parts[0].startswith('@') else parts[0]
                self.sdk_manifests.add(pkg.lower())

    # ---- parsers -------------------------------------------------------
    def parse_pbx(self, path):
        t = read_text(path)
        if not t:
            return
        self.types.add('xcode')
        self.tree[self.rel(path)] = hashlib.sha1(t.encode('utf-8', 'replace')).hexdigest()[:12]
        st = {}
        for k, v in re.findall(r'^\s*"?([A-Za-z_][\w\[\]=*~.]*)"?\s=\s(.+?);\s*$', t, re.M):
            st.setdefault(k, set()).add(v.strip('"'))
        for k in ('IPHONEOS_DEPLOYMENT_TARGET', 'MACOSX_DEPLOYMENT_TARGET', 'TVOS_DEPLOYMENT_TARGET',
                  'WATCHOS_DEPLOYMENT_TARGET', 'XROS_DEPLOYMENT_TARGET', 'TARGETED_DEVICE_FAMILY',
                  'SUPPORTS_MACCATALYST', 'PRODUCT_BUNDLE_IDENTIFIER', 'MARKETING_VERSION',
                  'CURRENT_PROJECT_VERSION', 'ENABLE_HARDENED_RUNTIME', 'ENABLE_APP_SANDBOX',
                  'CODE_SIGN_ENTITLEMENTS', 'SUPPORTED_PLATFORMS', 'SDKROOT', 'ARCHS',
                  'ASSETCATALOG_COMPILER_APPICON_NAME', 'GENERATE_INFOPLIST_FILE', 'LastUpgradeCheck',
                  'SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD', 'ENABLE_USER_SELECTED_FILES',
                  'ENABLE_OUTGOING_NETWORK_CONNECTIONS', 'ENABLE_INCOMING_NETWORK_CONNECTIONS'):
            if k in st:
                self.build.setdefault(k, set()).update(st[k])
        for k, vals in st.items():
            if k.startswith('INFOPLIST_KEY_'):
                key = k[len('INFOPLIST_KEY_'):].split('[')[0]
                val = sorted(vals)[0]
                self.plists.setdefault('(build settings)', {})[key] = val
                if key.endswith('UsageDescription'):
                    self.usage[key] = val
        for sdk in st.get('SDKROOT', ()):
            if sdk in SDK_PLATFORM:
                self.platforms.add(SDK_PLATFORM[sdk])
        for sp in st.get('SUPPORTED_PLATFORMS', ()):
            for w in sp.split():
                if w in SDK_PLATFORM:
                    self.platforms.add(SDK_PLATFORM[w])
        if 'YES' in st.get('SUPPORTS_MACCATALYST', ()):
            self.platforms.add('macos')
            self.notes.append('Mac Catalyst is enabled: the Mac build is reviewed under Mac App Store rules too.')
        for pt in re.findall(r'productType = "([^"]+)"', t):
            self.targets.append(PRODUCT_TYPES.get(pt, pt.rsplit('.', 1)[-1]))
        for url in re.findall(r'repositoryURL = "([^"]+)"', t):
            self.deps.add(url.rstrip('/').rsplit('/', 1)[-1].removesuffix('.git'))

    def parse_info_plist(self, path, rel, text):
        d = load_plist(path)
        if not d or ('CFBundleIdentifier' not in d and 'NSExtension' not in d
                     and not any(k.endswith('UsageDescription') for k in d)):
            return
        keep = {k: simple(d[k]) for k in PLIST_KEYS if k in d}
        for k, v in d.items():
            if k.endswith('UsageDescription'):
                self.usage[k] = str(v)
        self.plists[rel] = keep

    def parse_entitlements(self, path, rel, text):
        self.entitlements[rel] = simple(load_plist(path))

    def parse_manifest(self, path, rel, text):
        d = load_plist(path)
        self.manifests[rel] = {
            'tracking': d.get('NSPrivacyTracking'),
            'tracking_domains': simple(d.get('NSPrivacyTrackingDomains', [])),
            'collected': [x.get('NSPrivacyCollectedDataType') for x in d.get('NSPrivacyCollectedDataTypes', []) if isinstance(x, dict)],
            'api_types': {x.get('NSPrivacyAccessedAPIType'): x.get('NSPrivacyAccessedAPITypeReasons', [])
                          for x in d.get('NSPrivacyAccessedAPITypes', []) if isinstance(x, dict)},
        }

    def parse_config(self, path, rel, text):
        fn = os.path.basename(path)
        if fn == 'Podfile.lock':
            self.types.add('cocoapods')
            self.deps.update(m.split('/')[0] for m in re.findall(r'^  - "?([\w+\-./]+)', text, re.M))
        elif fn == 'Package.resolved':
            self.deps.update(re.findall(r'"(?:identity|package)"\s*:\s*"([^"]+)"', text))
        elif fn == 'Package.swift':
            self.types.add('swiftpm')
            self.deps.update(u.rstrip('/').rsplit('/', 1)[-1].removesuffix('.git') for u in re.findall(r'\.package\(\s*url:\s*"([^"]+)"', text))
            for p, name in (('ios', 'iOS'), ('macos', 'macOS'), ('tvos', 'tvOS'), ('watchos', 'watchOS'), ('visionos', 'visionOS')):
                if re.search(r'\.%s\(' % name, text) and not self.xcodeprojs:
                    self.platforms.add(p)
        elif fn.startswith('Cartfile'):
            self.deps.update(re.findall(r'"[\w.\-]+/([\w.\-]+)"', text))
        elif fn == 'package.json':
            try:
                pj = json.loads(text)
            except ValueError:
                return
            deps = {**pj.get('dependencies', {}), **pj.get('devDependencies', {})}
            apple = [k for k in deps if k in ('react-native', 'expo', '@capacitor/ios', 'cordova-ios', 'electron',
                                              '@tauri-apps/api', '@nativescript/core', 'react-native-macos')]
            if not apple:
                return  # a plain web package inside a monorepo is not part of the app bundle
            self.deps.update(pj.get('dependencies', {}))
            for k, t in (('react-native', 'react-native'), ('expo', 'expo'), ('@capacitor/ios', 'capacitor'),
                         ('cordova-ios', 'cordova'), ('electron', 'electron'), ('@tauri-apps/api', 'tauri')):
                if k in deps:
                    self.types.add(t)
            if 'electron' in deps or 'react-native-macos' in deps:
                self.platforms.add('macos')
            if {'react-native', 'expo', '@capacitor/ios', 'cordova-ios'} & set(deps):
                self.platforms.add('ios')
        elif fn == 'pubspec.yaml':
            self.types.add('flutter')
            m = re.search(r'^dependencies:\n((?:[ \t]+.*\n|\n)+)', text, re.M)
            if m:
                self.deps.update(re.findall(r'^  ([\w]+):', m.group(1), re.M))
            base = os.path.dirname(path)
            for p in ('ios', 'macos'):
                if os.path.isdir(os.path.join(base, p)):
                    self.platforms.add(p)
        elif fn in ('app.json', 'app.config.js', 'app.config.ts'):
            if '"expo"' in text or 'expo' in fn or 'infoPlist' in text:
                self.types.add('expo')
                for k, v in re.findall(r'["\']?(NS\w+UsageDescription)["\']?\s*:\s*["\'](.*?)["\']\s*[,}\n]', text):
                    self.usage[k] = v
                if not os.path.isdir(os.path.join(os.path.dirname(path), 'ios')):
                    self.notes.append(f'{rel}: Expo managed project with no ios/ directory. Info.plist and entitlements are generated at build time; verify them with `npx expo prebuild` or `npx expo config --type introspect`.')
        elif fn == 'project.yml':
            self.types.add('xcodegen')
            self.notes.append(f'{rel} (XcodeGen) is the source of truth: the .xcodeproj and any Info.plist it names are generated. Cite and fix {rel}, not the generated files.')
            m = re.search(r'MARKETING_VERSION:\s*"?([\w.]+)', text)
            if m:
                self.build.setdefault('MARKETING_VERSION', set()).add(m.group(1))
            for k, v in re.findall(r'^\s*(NS\w+UsageDescription):\s*(.+)$', text, re.M):
                self.usage.setdefault(k, v.strip().strip('"\''))
            for plat, name in (('ios', 'iOS'), ('macos', 'macOS'), ('tvos', 'tvOS'), ('watchos', 'watchOS'), ('visionos', 'visionOS')):
                m = re.search(r'^\s*%s:\s*"?([\d.]+)' % name, text, re.M)
                if m:
                    self.build.setdefault({'ios': 'IPHONEOS', 'macos': 'MACOSX', 'tvos': 'TVOS', 'watchos': 'WATCHOS', 'visionos': 'XROS'}[plat] + '_DEPLOYMENT_TARGET', set()).add(m.group(1))
                if re.search(r'^\s*platform:\s*\[?[^\n]*\b%s\b' % name, text, re.M):
                    self.platforms.add(plat)
        elif fn.startswith('capacitor.config'):
            self.types.add('capacitor')
        elif fn == 'config.xml' and '<widget' in text:
            self.types.add('cordova')
        elif fn == 'tauri.conf.json':
            self.types.add('tauri')
            self.platforms.add('macos')
        elif fn.startswith('electron-builder'):
            self.types.add('electron')
            self.platforms.add('macos')
            if not re.search(r'\bmas\b', text):
                self.notes.append(f'{rel}: no "mas" target found. Mac App Store builds of Electron apps need the mas target with sandbox entitlements.')
        elif fn == 'Cargo.toml':
            self.types.add('rust')
            m = re.search(r'^\[dependencies\]\n((?:(?!\[).*\n?)*)', text, re.M)
            if m:
                self.deps.update('crate:' + x for x in re.findall(r'^([\w\-]+)\s*=', m.group(1), re.M))

    def check_icon(self, d):
        info = {'path': self.rel(d), 'images': 0, 'alpha': None}
        cj = read_json(os.path.join(d, 'Contents.json'), {}) or {}
        files = [i.get('filename') for i in cj.get('images', []) if i.get('filename')]
        info['images'] = len(files)
        for f in files:
            p = os.path.join(d, f)
            try:
                r = subprocess.run(['sips', '-g', 'hasAlpha', '-g', 'pixelWidth', p], capture_output=True, text=True, timeout=10)
                if 'pixelWidth: 1024' in r.stdout or len(files) == 1:
                    info['alpha'] = 'hasAlpha: yes' in r.stdout
                    info['size_1024'] = 'pixelWidth: 1024' in r.stdout
                    break
            except (OSError, subprocess.SubprocessError):
                break
        self.icons.append(info)

    def parse_metadata(self, d):
        lim = self.req['limits']
        out = {'path': self.rel(d), 'locales': {}, 'problems': []}
        for loc in sorted(os.listdir(d)):
            ld = os.path.join(d, loc)
            if not os.path.isdir(ld) or loc == 'review_information':
                continue
            fields = {}
            for fn in os.listdir(ld):
                if fn.endswith('.txt'):
                    val = (read_text(os.path.join(ld, fn)) or '').strip()
                    key = fn[:-4]
                    fields[key] = len(val)
                    if key in lim and len(val) > lim[key]:
                        out['problems'].append(f'{loc}/{fn}: {len(val)} chars, limit {lim[key]}')
                    if key in ('name', 'subtitle', 'keywords', 'privacy_url', 'support_url', 'marketing_url') and loc in ('en-US', 'default'):
                        out.setdefault('values', {})[key] = val[:200]
            out['locales'][loc] = fields
        ri = os.path.join(d, 'review_information')
        out['review_information'] = sorted(os.listdir(ri)) if os.path.isdir(ri) else None
        self.metadata = out

    # ---- derived -------------------------------------------------------
    def finish(self):
        # dependencies also count as evidence for SDK signals
        if self.deps:
            self.grep('(dependency list)', '\n'.join(sorted(self.deps)), 'code')
        if not self.platforms:
            if any(k.startswith('IPHONEOS') for k in self.build) or 'xcodegen' in self.types:
                self.platforms.add('ios')
        if not self.platforms and (self.plists or self.code_files):
            self.platforms.add('ios')
            self.notes.append('Platform could not be determined from project files; assuming iOS. Pass --platform to override.')
        fam = ','.join(sorted(self.build.get('TARGETED_DEVICE_FAMILY', [])))
        self.devices = sorted({{'1': 'iPhone', '2': 'iPad', '3': 'Apple TV', '4': 'Apple Watch', '7': 'Apple Vision'}.get(x, x)
                               for x in re.findall(r'\d', fam)})
        try:
            r = subprocess.run(['xcodebuild', '-version'], capture_output=True, text=True, timeout=15)
            self.xcode = r.stdout.split('\n')[0].strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            self.xcode = None

    def on(self, name):
        return self.sig[name]['count'] > 0

    def plist_value(self, key):
        for d in self.plists.values():
            if key in d:
                return d[key]
        return None

    def hints(self):
        H = []

        def add(area, check, level, msg):
            H.append({'area': area, 'check': check, 'level': level, 'msg': msg})

        req, ios_family = self.req, bool(self.platforms - {'macos'})
        have_plist = bool(self.plists) or bool(self.usage)
        # purpose strings
        for sig, keys in PURPOSE.items():
            if self.on(sig) and not any(k in self.usage for k in keys):
                if have_plist:
                    add('permissions', 'PERM-01', 'fail', f'Code uses {sig} APIs but no {" / ".join(keys)} was found. The app crashes on first access without it.')
                else:
                    add('permissions', 'PERM-01', 'check', f'Code uses {sig} APIs; no Info.plist was found to confirm {keys[0]}.')
        if self.on('local_network') and 'NSLocalNetworkUsageDescription' not in self.usage and 'ios' in self.platforms:
            add('permissions', 'PERM-01', 'check', 'Local-network style APIs are used but NSLocalNetworkUsageDescription is missing. Needed if the app browses or connects to devices on the LAN.')
        for k, v in self.usage.items():
            if len(v.strip()) < 30 or re.search(r'^\$\(|needs? access|requires? access|would like to access|^[\w ]+ (uses|accesses) (the|your) \w+\.?$', v.strip(), re.I):
                add('permissions', 'PERM-02', 'warn', f'{k} is vague or too short ("{v[:80]}"). Say what the data is used for, with an example.')
        used = {k for sig, keys in PURPOSE.items() if self.on(sig) for k in keys}
        used |= {'NSLocalNetworkUsageDescription', 'NSPhotoLibraryAddUsageDescription'}
        for k in self.usage:
            if k not in used and k.endswith('UsageDescription') and self.code_files:
                add('permissions', 'PERM-03', 'check', f'{k} is declared but no matching API use was detected. Unused permissions invite a 5.1.1 question; remove it or confirm an SDK needs it.')
        # privacy manifest + required-reason APIs (not enforced for macOS-only apps)
        if ios_family:
            declared = set()
            for m in self.manifests.values():
                declared |= set(m['api_types'])
            usedrr = [RR_CATEGORY[s] for s in RR_CATEGORY if self.on(s)]
            if not self.manifests:
                add('permissions', 'PERM-04', 'fail' if usedrr else 'warn',
                    'No PrivacyInfo.xcprivacy in the app' + (f'; first-party code uses required-reason APIs: {", ".join(c.replace("NSPrivacyAccessedAPICategory", "") for c in usedrr)}. Upload is rejected (ITMS-91053) without declared reasons.' if usedrr else '.'))
            else:
                for c in usedrr:
                    if c not in declared:
                        add('permissions', 'PERM-04', 'fail', f'{c} is used in code but not declared in the privacy manifest (allowed reasons: {", ".join(req["required_reason_apis"][c])}).')
                for c, reasons in ((c, r) for m in self.manifests.values() for c, r in m['api_types'].items()):
                    bad = [r for r in reasons if r not in req['required_reason_apis'].get(c, [])]
                    if bad:
                        add('permissions', 'PERM-04', 'fail', f'Privacy manifest declares unknown reason(s) {bad} for {c}.')
        listed = {s.lower(): s for s in req['listed_sdks']}
        present = sorted({listed[d.lower()] for d in self.deps if d.lower() in listed})
        self.listed_present = present
        if present:
            missing = [p for p in present if self.dep_dirs_seen and not any(p.lower() in m for m in self.sdk_manifests)]
            add('permissions', 'PERM-05', 'check', f'Apple-listed SDKs present (each must ship a privacy manifest and, as a binary, a signature): {", ".join(present)}.'
                + (f' No manifest found in vendored copies of: {", ".join(missing)}; update those.' if missing else ''))
        # tracking
        if (self.on('idfa') or self.on('ads_sdk')) and not self.on('att'):
            add('permissions', 'PERM-06', 'fail', 'Advertising SDK or IDFA use found but no App Tracking Transparency request.')
        if self.on('att') and 'NSUserTrackingUsageDescription' in self.usage and not any(m.get('tracking') for m in self.manifests.values()):
            add('permissions', 'PERM-06', 'warn', 'ATT is requested but the privacy manifest does not set NSPrivacyTracking / tracking domains.')
        ats = self.plist_value('NSAppTransportSecurity') or {}
        if isinstance(ats, dict) and ats.get('NSAllowsArbitraryLoads'):
            add('permissions', 'PERM-07', 'warn', 'NSAllowsArbitraryLoads is true: ATS is disabled app-wide. Expect to justify it; prefer per-domain exceptions.')
        if self.on('insecure_http') and not (isinstance(ats, dict) and (ats.get('NSAllowsArbitraryLoads') or ats.get('NSExceptionDomains') or ats.get('NSAllowsLocalNetworking'))):
            add('permissions', 'PERM-07', 'check', 'Plain http:// URLs appear in code with no ATS exception; those requests will fail at runtime.')
        if self.on('secrets'):
            add('permissions', 'PERM-11', 'fail', 'What looks like a live secret or private key is in source and will ship in the bundle.')
        # completeness
        cur, up = req['current'], req['upcoming']
        if self.xcode:
            major = vtuple(self.xcode)[0]
            if major < cur['min_xcode_major']:
                add('completeness', 'COMP-01', 'fail', f'Local {self.xcode} is below the required minimum: {cur["sdk"]}.')
            elif major < up['min_xcode_major']:
                add('completeness', 'COMP-01', 'check', f'Local {self.xcode} is accepted today; from {up["from"]} uploads need {up["sdk"]}.')
        for plat, key in (('ios', 'IPHONEOS_DEPLOYMENT_TARGET'),):
            for v in self.build.get(key, ()):
                if vtuple(v) < vtuple(cur['min_deployment'][plat]):
                    add('completeness', 'COMP-02', 'fail', f'{key} {v} is below the minimum accepted target ({cur["min_deployment"][plat]}).')
                elif vtuple(v) < vtuple(up['min_deployment'][plat]):
                    add('completeness', 'COMP-02', 'warn', f'{key} {v}: from {up["from"]} the minimum target is {up["min_deployment"][plat]}.')
        if self.on('placeholder'):
            add('completeness', 'COMP-03', 'check', f'{self.sig["placeholder"]["count"]} placeholder-looking string(s) found.')
        if self.on('beta_wording'):
            add('completeness', 'COMP-04', 'check', 'User-facing strings mention beta/demo/trial/preview.')
        if self.on('dev_endpoints'):
            add('completeness', 'COMP-05', 'check', 'Development or LAN endpoints are hardcoded; confirm release builds use live production services.')
        if 'xcode' in self.types or self.plists:
            if not self.icons:
                add('completeness', 'COMP-06', 'fail', 'No AppIcon.appiconset found. A build without an app icon is rejected at upload.')
            for ic in self.icons:
                if ic['images'] == 0:
                    add('completeness', 'COMP-06', 'fail', f'{ic["path"]} has no image files assigned.')
                elif ic.get('alpha') and ios_family:
                    add('completeness', 'COMP-06', 'fail', f'{ic["path"]}: the large app icon has an alpha channel (upload error ITMS-90717).')
            if 'ios' in self.platforms and have_plist and self.plist_value('UILaunchStoryboardName') is None \
                    and self.plist_value('UILaunchScreen') is None and not any(k.startswith('UILaunchScreen') or k == 'UILaunchStoryboardName' for k in self.plists.get('(build settings)', {})):
                add('completeness', 'COMP-07', 'fail', 'No launch screen (UILaunchScreen / UILaunchStoryboardName). The app runs letterboxed and iPad multitasking validation fails.')
            if have_plist and self.plist_value('ITSAppUsesNonExemptEncryption') is None:
                add('completeness', 'COMP-08', 'check', 'ITSAppUsesNonExemptEncryption is not set; App Store Connect will ask the export-compliance question on every upload.')
        sv = self.plist_value('CFBundleShortVersionString')
        mv = sorted(self.build.get('MARKETING_VERSION', ()))
        if isinstance(sv, str) and '$(' not in sv and mv and sv not in mv:
            add('completeness', 'COMP-12', 'check', f'Info.plist CFBundleShortVersionString is the literal "{sv}" but MARKETING_VERSION is {mv}. The plist literal is what ships; use $(MARKETING_VERSION) so they cannot drift.')
        if self.on('custom_crypto'):
            add('completeness', 'COMP-08', 'check', 'Cryptography code or libraries are referenced; the export-compliance answer depends on what they are used for.')
        for v in self.build.get('PRODUCT_BUNDLE_IDENTIFIER', ()):
            if re.search(r'com\.example|com\.yourcompany|org\.reactjs\.native\.example|com\.company\.', v):
                add('completeness', 'COMP-12', 'fail', f'Bundle identifier looks like a template default: {v}.')
        # technical
        if self.on('uiwebview'):
            add('technical', 'TECH-02', 'fail', 'UIWebView is referenced. Binaries containing it are rejected (ITMS-90809).')
        if self.on('mining'):
            add('technical', 'TECH-08', 'fail', 'Cryptocurrency-mining strings found.')
        modes = self.plist_value('UIBackgroundModes') or []
        if modes:
            add('technical', 'TECH-04', 'check', f'UIBackgroundModes declared: {modes}. Each needs a user-visible feature that uses it.')
        if 'ios' in self.platforms and self.devices and 'iPad' not in self.devices and 'iPhone' in self.devices:
            add('technical', 'TECH-11', 'check', 'Target is iPhone-only; Apple expects iPhone apps to run on iPad when possible.')
        # accounts / payments / ugc / design
        if self.on('third_party_login') and not self.on('sign_in_with_apple'):
            add('accounts', 'ACCT-01', 'fail', 'Third-party or social login found without Sign in with Apple (or an equivalent privacy-preserving option).')
        if (self.on('account_creation') or self.on('login')) and not self.on('account_deletion'):
            add('accounts', 'ACCT-02', 'fail' if self.on('account_creation') else 'check', 'Sign-in or account creation found but nothing that looks like in-app account deletion.')
        if self.on('storekit') and not self.on('restore_purchases'):
            add('payments', 'PAY-03', 'fail', 'In-app purchase code found but no restore-purchases path.')
        if self.on('external_payment') and (self.on('paywall_copy') or self.on('storekit')):
            add('payments', 'PAY-01', 'check', 'A third-party payment SDK sits alongside paywall or subscription wording. Digital goods must use in-app purchase.')
        if self.on('ugc') and not self.on('moderation'):
            add('ugc', 'UGC-02', 'fail', 'User-generated content signals found but no report, block or moderation code.')
        if self.on('custom_review_prompt'):
            add('design', 'DES-05', 'check', 'Custom "rate us" style wording found; review prompts must go through the system API.')
        if self.on('other_platforms'):
            add('metadata', 'META-04', 'check', 'User-facing strings mention other platforms or stores.')
        for p in self.metadata.get('problems', []):
            add('metadata', 'META-01', 'fail', f'Metadata over limit: {p}.')
        name = self.plist_value('CFBundleDisplayName')
        if isinstance(name, str) and len(name) > req['limits']['name']:
            add('metadata', 'META-01', 'warn', f'CFBundleDisplayName is {len(name)} characters; the App Store name limit is {req["limits"]["name"]}.')
        # macOS
        if 'macos' in self.platforms:
            ent = [e for e in self.entitlements.values()]
            sandbox = any(e.get('com.apple.security.app-sandbox') for e in ent) or 'YES' in self.build.get('ENABLE_APP_SANDBOX', ())
            if not sandbox:
                add('macos', 'MAC-01', 'fail', 'No App Sandbox entitlement found. Mac App Store apps must be sandboxed.')
            temp = sorted({k for e in ent for k in e if 'temporary-exception' in k})
            if temp:
                add('macos', 'MAC-02', 'warn', f'Temporary-exception entitlements need written justification and are often refused: {", ".join(temp)}.')
            for sig, check, msg in (('mac_updater', 'MAC-03', 'A self-update mechanism is referenced; Mac App Store builds must update only through the store.'),
                                    ('license_key', 'MAC-04', 'License-key or activation wording found; Mac App Store apps may not use their own licensing.'),
                                    ('mac_privileged', 'MAC-06', 'Privilege-escalation APIs or helpers are referenced.'),
                                    ('mac_installs_code', 'MAC-07', 'Code that installs or downloads additional software is referenced.')):
                if self.on(sig):
                    add('macos', check, 'check', msg)
        return H

    def areas(self, hints):
        on, A = self.on, {}

        def put(aid, state, why):
            A[aid] = {'apply': state, 'why': why}

        for aid, (_t, always) in AREAS.items():
            if always:
                put(aid, 'yes', 'always')
        why = [s for s in ('login', 'third_party_login', 'sign_in_with_apple', 'account_creation') if on(s)]
        put('accounts', 'yes' if why else 'no', why)
        strong = [s for s in ('storekit', 'external_payment', 'apple_pay', 'external_purchase_link', 'loot_box', 'virtual_currency') if on(s)]
        weak = [s for s in ('paywall_copy', 'license_key', 'tipping', 'crypto') if on(s)]
        put('payments', 'yes' if strong else 'maybe' if weak else 'no', strong + weak)
        strong = [s for s in ('ugc', 'ai_generation', 'anonymous_chat') if on(s)]
        weak = [s for s in ('third_party_ai', 'moderation', 'mini_apps') if on(s)]
        put('ugc', 'yes' if strong else 'maybe' if weak else 'no', strong + weak)
        put('kids', 'maybe' if on('kids') else 'no', ['kids'] if on('kids') else [])
        strong = ['healthkit'] if on('healthkit') else []
        weak = ['medical_claims'] if self.sig['medical_claims']['count'] >= 2 else []
        put('health', 'yes' if strong else 'maybe' if weak else 'no', strong + weak)
        strong = [s for s in ('vpn', 'mdm') if on(s)]
        weak = [s for s in ('gambling', 'crypto', 'finance', 'substances', 'crime_reporting') if on(s)]
        put('regulated', 'yes' if strong else 'maybe' if weak else 'no', strong + weak)
        ext_targets = sorted({t for t in self.targets if t not in ('app',) and not t.startswith(('unit-test', 'ui-testing', 'bundle', 'framework', 'library', 'tool'))})
        why = ext_targets + [s for s in ('siri_intents', 'widgets', 'callkit', 'keyboard_ext') if on(s)]
        put('extensions', 'yes' if why else 'no', why)
        put('macos', 'yes' if 'macos' in self.platforms else 'no', ['macOS target'] if 'macos' in self.platforms else [])
        other = sorted(self.platforms & {'tvos', 'watchos', 'visionos'}) + [t for t in ext_targets if t.startswith('watch')]
        put('tv-watch-vision', 'yes' if other else 'no', other)
        return A

    def profile(self):
        hints = self.hints()
        return {
            'generated_at': now(),
            'root': self.root,
            'exclude': list(self.exclude),
            'requirements_as_of': self.req['as_of'],
            'git': git_state(self.root),
            'project_types': sorted(self.types),
            'platforms': sorted(self.platforms),
            'devices': self.devices,
            'xcodeprojs': self.xcodeprojs,
            'xcode': self.xcode,
            'targets': sorted(set(self.targets)),
            'build': {k: sorted(v) for k, v in self.build.items()},
            'plists': self.plists,
            'usage_descriptions': self.usage,
            'entitlements': self.entitlements,
            'privacy_manifests': self.manifests,
            'sdk_manifests_found': sorted(self.sdk_manifests)[:200],
            'dependencies': sorted(self.deps)[:300],
            'listed_sdks_present': self.listed_present,
            'icons': self.icons,
            'bundled_assets': self.assets,
            'license_files': self.licenses[:30],
            'metadata': self.metadata,
            'notes': self.notes,
            'code_files': self.code_files,
            'areas': self.areas(hints),
            'hints': hints,
            'signals': {k: v for k, v in self.sig.items() if v['count']},
            'tree': self.tree,
        }


# ---- output ------------------------------------------------------------
def tree_diff(old, new):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    modified = sorted(k for k in new if k in old and old[k] != new[k])
    return added, modified, removed


def fmt(v):
    return json.dumps(v, separators=(',', ':'), ensure_ascii=False)


def print_overview(p, od):
    print(f"# app-store-scan preflight  ({p['generated_at']})")
    print(f"project: {p['root']}")
    print(f"type: {', '.join(p['project_types']) or 'unknown'} | platforms: {', '.join(p['platforms']) or '?'}"
          f" | devices: {', '.join(p['devices']) or '?'} | {p['code_files']} source files")
    if p['xcodeprojs']:
        print(f"xcode projects: {', '.join(p['xcodeprojs'])} | targets: {', '.join(p['targets'])}")
    print(f"git: {describe_git(p['git'])}")
    if p['exclude']:
        print(f"excluded (not part of the shipped app): {', '.join(p['exclude'])}")
    for n in p['notes']:
        print(f"note: {n}")
    if not p['code_files']:
        print('WARNING: no source files found. Is this the app directory?')
    print('\n## areas  (apply | last scanned | changes since)')
    for aid, a in p['areas'].items():
        snap = read_json(os.path.join(od, 'snapshots', aid + '.json'))
        prev = read_json(os.path.join(od, 'findings', aid + '.json'))
        nh = sum(1 for h in p['hints'] if h['area'] == aid)
        line = f"- {aid}: {a['apply']}"
        if a['why'] and a['why'] != 'always':
            line += f" ({', '.join(a['why'][:6])})"
        if nh:
            line += f" | {nh} hint(s)"
        if snap:
            ad, mo, rm = tree_diff(snap.get('tree', {}), p['tree'])
            ch = ad + mo + rm
            st = ''
            if prev:
                c = {}
                for k in prev.get('checks', []):
                    c[k.get('status')] = c.get(k.get('status'), 0) + 1
                st = ' [' + ' '.join(f'{k}:{v}' for k, v in sorted(c.items())) + ']'
            line += f" | scanned {snap.get('at', '?')[:16]}{st} | "
            line += 'UNCHANGED since then' if not ch else f"{len(ch)} file(s) changed: {', '.join(ch[:12])}{' ...' if len(ch) > 12 else ''}"
        elif a['apply'] != 'no':
            line += ' | never scanned'
        print(line)
    hist = read_json(os.path.join(od, 'history.json'), [])
    if hist:
        last = hist[-1]
        print(f"\n## last recorded run: {last['at'][:16]} at {describe_git(last.get('git'))}; areas: {', '.join(last.get('areas', []))}")
        old = (last.get('git') or {}).get('commit')
        cur = (p['git'] or {}).get('commit')
        if old and cur and old != cur:
            log = git_log_between(p['root'], old)
            print(f"commits since ({len(log)}{'+' if len(log) >= 15 else ''}):")
            for ln in log:
                print(f"  {ln}")
        elif old and old == cur:
            print('same commit as last run; differences are uncommitted changes only.')
    print(f"\nNext: detect.py <project> --area <id>[,<id>] for evidence. State dir: {od}")


def print_area(p, aid, od):
    print(f"\n# area: {aid} — {AREAS[aid][0]}  (apply: {p['areas'][aid]['apply']})")
    snap = read_json(os.path.join(od, 'snapshots', aid + '.json'))
    if snap:
        ad, mo, rm = tree_diff(snap.get('tree', {}), p['tree'])
        print(f"last scanned {snap.get('at', '?')[:16]} at {describe_git(snap.get('git'))}; previous findings: {OUT_DIR}/findings/{aid}.json")
        if ad or mo or rm:
            print(f"changed since: +{len(ad)} ~{len(mo)} -{len(rm)}: {', '.join((ad + mo + rm)[:40])}")
        else:
            print('no scanned file has changed since.')
    else:
        print('previous findings: none (first scan of this area)')
    for n in p['notes']:
        print(f'note: {n}')
    hs = [h for h in p['hints'] if h['area'] == aid]
    if hs:
        print('## hints (deterministic; verify before reporting)')
        for h in hs:
            print(f"- [{h['check']}|{h['level']}] {h['msg']}")
    facts = {
        'completeness': ['xcode', 'build', 'icons', 'targets'],
        'technical': ['build', 'entitlements'],
        'permissions': ['usage_descriptions', 'privacy_manifests', 'listed_sdks_present', 'entitlements'],
        'privacy': ['privacy_manifests', 'dependencies', 'usage_descriptions'],
        'metadata': ['metadata', 'icons', 'build'],
        'design': ['devices', 'usage_descriptions'],
        'content': ['bundled_assets', 'license_files', 'dependencies'],
        'accounts': ['entitlements'],
        'payments': ['entitlements'],
        'extensions': ['targets', 'entitlements'],
        'macos': ['entitlements', 'build'],
        'tv-watch-vision': ['targets', 'build'],
    }.get(aid, [])
    if facts or aid in ('completeness', 'technical', 'permissions', 'metadata', 'macos', 'extensions'):
        print('## facts')
        for k in facts:
            if p.get(k):
                print(f"{k}: {fmt(p[k])[:3000]}")
        if aid in ('completeness', 'technical', 'permissions', 'metadata', 'macos', 'extensions', 'design', 'content'):
            for path, d in p['plists'].items():
                print(f"plist {path}: {fmt(d)[:2500]}")
    names = [n for n, areas, *_ in SIGNALS if aid in areas.split(',')]
    live = [n for n in names if n in p['signals']]
    print('## signals (grep evidence; a signal is a lead, not a finding)')
    for n in live:
        s = p['signals'][n]
        print(f"{n}: {s['count']} match(es) in {s['files']} file(s)")
        for h in s['hits']:
            print(f"  {h['file']}:{h['line']}: {h['text']}")
    quiet = [n for n in names if n not in p['signals']]
    if quiet:
        print(f"no matches: {', '.join(quiet)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--area', help='comma-separated area ids to print evidence for')
    ap.add_argument('--platform', help='override detected platforms, e.g. ios or ios,macos')
    ap.add_argument('--exclude', help='comma-separated paths (relative to project) that are not part of the shipped app; remembered for later runs. Pass an empty string to clear.')
    ap.add_argument('--hits', type=int, default=8, help='max evidence lines kept per signal')
    a = ap.parse_args()
    if not os.path.isdir(a.project):
        sys.exit(f'not a directory: {a.project}')
    od = out_dir(os.path.abspath(a.project))
    cfg_path = os.path.join(od, 'config.json')
    cfg = read_json(cfg_path, {}) or {}
    if a.exclude is not None:
        cfg['exclude'] = [x.strip().strip('/') for x in a.exclude.split(',') if x.strip()]
    if a.platform:
        cfg['platform'] = [x.strip().lower() for x in a.platform.split(',')]
    if a.exclude is not None or a.platform:
        write_json(cfg_path, cfg)
    s = Scan(a.project, a.hits, cfg.get('exclude', ()))
    s.run()
    if cfg.get('platform'):
        s.platforms = set(cfg['platform'])
    p = s.profile()
    write_json(os.path.join(od, 'profile.json'), p)
    if a.area:
        ids = [x.strip() for x in a.area.split(',') if x.strip()]
        bad = [x for x in ids if x not in AREAS]
        if bad:
            sys.exit(f"unknown area(s): {', '.join(bad)}. Valid: {', '.join(AREAS)}")
        print(f"project: {p['root']} | platforms: {', '.join(p['platforms'])} | git: {describe_git(p['git'])}")
        for x in ids:
            print_area(p, x, od)
    else:
        print_overview(p, od)


if __name__ == '__main__':
    main()
