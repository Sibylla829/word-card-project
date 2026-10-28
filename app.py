import streamlit as st
from datetime import date, datetime
import json
import os
import random
import base64
import re
import hashlib

# ===================== 页面基础设置 =====================
st.set_page_config(
    page_title="💖单词背诵打卡系统｜🐱宠物小猫",
    page_icon="🐱",
    layout="centered"
)

DATA_DIR = "user_data"           # 每个用户的独立存档目录
LEGACY_FILE = "word_data.json"   # 旧版公共存档（仅用于一次性迁移导入）

# ===================== 气泡文案库 =====================
praise_list = [
    "太棒啦！🥳学得好快！",
    "厉害厉害！💯继续保持！",
    "真不错，一下子就记住咯～✨",
    "聪明小猫的主人就是你！🐱",
    "哇塞，又答对啦！🎉"
]

comfort_list = [
    "没关系，再接再厉！💪",
    "差一点点，多看几遍就会啦",
    "不要灰心，我们再试一次😊",
    "慢慢来，单词本来就很难哒",
    "这次错了，下次一定可以！"
]

# ===================== base64图片编码工具 =====================
def get_img_base64(file_path):
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ===================== 宠物图片路径 =====================
PET_IMAGES = {
    "cat_base": "pet_images/cat_base.png",
    "cat_sweater": "pet_images/cat_sweater.png",
    "cat_bow": "pet_images/cat_bow.png",
    "cat_crown": "pet_images/cat_crown.png",
    "cat_fish": "pet_images/cat_fish.png",
    "cat_can": "pet_images/cat_can.png",
    "cat_teaser": "pet_images/cat_teaser.png",
}

# ===================== 数据持久化函数（每个用户独立存档） =====================

def safe_userid(uid):
    """把用户ID转成安全的文件名（去掉路径非法字符）"""
    name = re.sub(r'[\\/:*?"<>|\s]', '_', str(uid)).strip("_")
    return name or "user"

def user_file(userid):
    """某个用户的存档文件路径：user_data/<用户ID>.json"""
    return os.path.join(DATA_DIR, f"{safe_userid(userid)}.json")

def hash_pwd(pwd):
    """密码哈希（不存明文）"""
    return hashlib.sha256(("wordcat-salt::" + str(pwd)).encode("utf-8")).hexdigest()

def collect_data():
    """把当前会话数据打包成存档字典"""
    return {
        "marked": st.session_state.marked,
        "wrong_words": st.session_state.wrong_words,
        "checkin_date": str(st.session_state.checkin_date) if st.session_state.checkin_date else None,
        "last_index": st.session_state.last_index,
        "achievements": st.session_state.achievements,
        "daily_count": st.session_state.daily_count,
        "username": st.session_state.username,
        "userid": st.session_state.userid,
        "points": st.session_state.points,
        "spell_date": str(st.session_state.spell_date),
        "today_spell_record": st.session_state.today_spell_record,
        "pet": st.session_state.pet,
        "backpack": st.session_state.backpack,
        "pet_last_decay_time": st.session_state.pet_last_decay_time,
        "pet_temp_image": st.session_state.pet_temp_image,
        "pet_temp_until": st.session_state.pet_temp_until,
        "used_codes": st.session_state.get("used_codes", []),
        "spell_bonus_got": st.session_state.get("spell_bonus_got", False),
        "last_bubble_text": st.session_state.get("last_bubble_text", "今天也要好好学单词哦🐱"),
        "custom_words": st.session_state.get("custom_words", []),  # 用户自定义词库（随档保存）
    }

def save_data():
    """保存当前登录用户的数据到 user_data/<用户ID>.json（未登录则不写）"""
    if not st.session_state.get("logged_in"):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    data = collect_data()
    data["pwd_hash"] = st.session_state.get("pwd_hash", "")
    with open(user_file(st.session_state.userid), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_user_data(userid):
    """读取某个用户的存档；不存在返回 None"""
    path = user_file(userid)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def init_default_session():
    """初始化一份全新的默认数据（新用户 / 登录前的基底）"""
    st.session_state.marked = {}
    st.session_state.wrong_words = []
    st.session_state.checkin_date = None
    st.session_state.last_index = {"小学单词":0,"初中单词":0,"高中单词":0,"四六级单词":0}
    st.session_state.achievements = []
    st.session_state.daily_count = 0
    st.session_state.username = ""
    st.session_state.userid = ""
    st.session_state.focus_start = None
    st.session_state.focus_target_min = None
    st.session_state.points = 0
    st.session_state.spell_date = date.today()
    st.session_state.today_spell_record = []
    st.session_state.pet = {"name": "小粉猫", "hunger": 50, "happiness": 50, "equipped": []}
    st.session_state.backpack = []
    st.session_state.pet_last_decay_time = datetime.now().timestamp()
    st.session_state.pet_temp_image = None
    st.session_state.pet_temp_until = 0
    st.session_state.used_codes = []
    st.session_state.spell_bonus_got = False
    st.session_state.last_bubble_text = "今天也要好好学单词哦🐱"
    st.session_state.custom_words = []

def apply_saved(saved):
    """把读取到的存档覆盖到会话中"""
    st.session_state.marked = saved.get("marked", {})
    st.session_state.wrong_words = saved.get("wrong_words", [])
    cd = saved.get("checkin_date")
    st.session_state.checkin_date = date.fromisoformat(cd) if cd else None
    st.session_state.last_index = saved.get(
        "last_index", {"小学单词":0,"初中单词":0,"高中单词":0,"四六级单词":0})
    st.session_state.achievements = saved.get("achievements", [])
    st.session_state.daily_count = saved.get("daily_count", 0)
    st.session_state.username = saved.get("username", st.session_state.username)
    st.session_state.userid = saved.get("userid", st.session_state.userid)
    st.session_state.points = saved.get("points", 0)
    st.session_state.spell_date = date.fromisoformat(saved.get("spell_date", str(date.today())))
    st.session_state.today_spell_record = saved.get("today_spell_record", [])
    st.session_state.pet = saved.get("pet", st.session_state.pet)
    st.session_state.backpack = saved.get("backpack", [])
    st.session_state.pet_last_decay_time = saved.get("pet_last_decay_time", datetime.now().timestamp())
    st.session_state.pet_temp_image = saved.get("pet_temp_image", None)
    st.session_state.pet_temp_until = saved.get("pet_temp_until", 0)
    st.session_state.used_codes = saved.get("used_codes", [])
    st.session_state.spell_bonus_got = saved.get("spell_bonus_got", False)
    st.session_state.last_bubble_text = saved.get("last_bubble_text", "今天也要好好学单词哦🐱")
    st.session_state.custom_words = saved.get("custom_words", [])

# ===================== 💖粉色主题样式 =====================
st.markdown("""
<style>
    @keyframes fadeIn {
        0% {opacity:0; transform: translateY(20px);}
        100% {opacity:1; transform: translateY(0px);}
    }
    @keyframes bounce {
        0%,20%,50%,80%,100%{transform: translateY(0);}
        40%{transform: translateY(-12px);}
        60%{transform: translateY(-6px);}
    }
    @keyframes petFloat {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
        100% { transform: translateY(0px); }
    }
    .stApp {background: #fff0f6;}
    h1,h2,h3,.stMarkdown,.stText,label,.stSelectbox,.stMetric {color: black !important;}
    [data-testid="stMetricValue"] {color: black !important;}
    [data-testid="stMetricLabel"] {color: black !important;}
    h1 {text-align:center;color:#d63384 !important;animation:fadeIn 0.8s ease;}
    .word-card {
        background: linear-gradient(135deg,#ffd6e7,#ffecf4);
        padding:45px 30px;
        border-radius:24px;
        box-shadow:0 10px 24px rgba(214,51,132,0.18);
        text-align:center;
        margin:24px 0px;
        animation:fadeIn 0.6s ease;
    }
    .en-word {font-size:38px;font-weight:bold;color:black !important;}
    .cn-mean {font-size:30px;color:black !important;margin-top:18px;}
    .hide-text {font-size:30px;color:#cc88aa;}
    .stButton > button {
        width:100%;
        border:none;padding:12px;border-radius:14px;font-size:16px;
        box-shadow:0 4px 10px rgba(0,0,0,0.12);transition:0.25s;
    }
    .btn-green > button {background-color:#51cf66 !important;color:white !important;}
    .btn-red > button {background-color:#ff6b6b !important;color:white !important;}
    .btn-pink > button {background-color:#ff79c6 !important;color:white !important;}
    .btn-gold > button {background-color:#ffc107 !important;color:black !important;}
    .stButton > button:hover {transform: translateY(-3px);animation:bounce 0.6s ease;}
    .wrong-card {
        background:#fff5f9;border-left:5px solid #ff79c6;
        padding:12px 18px;margin:8px 0;border-radius:12px;color:black !important;
    }
    .pet-card {
        background: linear-gradient(135deg,#ffe4f1,#fff7fb);
        padding:30px;border-radius:24px;
        box-shadow:0 10px 24px rgba(214,51,132,0.15);
        text-align:center;
        margin:20px 0;
    }
    /* ===== 全局可拖拽悬浮宠物 ===== */
    #petBox{
        position:fixed;
        bottom:24px;
        right:24px;
        z-index:99999;
        display:flex;
        align-items:flex-end;
        gap:10px;
        animation: petFloat 2.5s ease-in-out infinite;
        cursor: move;
        user-select: none;
    }
    #petBox.dragging{
        animation:none !important;
    }
    .bubble{
        background:#ffffff;
        border:2px solid #ffb8d9;
        border-radius:16px 16px 16px 4px;
        padding:10px 14px;
        max-width:180px;
        font-size:14px;
        box-shadow:0 4px 12px #00000018;
    }
    .float-pet-img{
        width:70px;
        border-radius:999px;
    }
</style>
""", unsafe_allow_html=True)

st.title("💖单词背诵打卡系统｜🐱宠物小猫")

# ===================== 🔐 登录 / 注册（每人独立存档） =====================
if not st.session_state.get("logged_in"):
    st.subheader("🔐 账号")
    st.caption("每个账号拥有完全独立的存档：学习进度、错题本、积分、宠物、自定义单词都只属于你自己。")

    # 单选切换登录/注册，注册入口更显眼
    mode = st.radio("请选择", ["🔑 登录已有账号", "🆕 注册新用户（第一次使用点这里）"],
                    horizontal=True, label_visibility="collapsed")

    if mode == "🔑 登录已有账号":
        login_id = st.text_input("用户ID", key="login_id")
        login_pwd = st.text_input("密码", type="password", key="login_pwd")
        if st.button("登 录", type="primary", use_container_width=True):
            uid = login_id.strip()
            if not uid:
                st.error("请输入用户ID！")
            else:
                saved = load_user_data(uid)
                if saved is None:
                    st.error("该用户ID不存在，请先注册～")
                elif saved.get("pwd_hash") != hash_pwd(login_pwd):
                    st.error("密码错误！")
                else:
                    init_default_session()
                    apply_saved(saved)
                    st.session_state.userid = uid           # 以登录输入的ID为准
                    st.session_state.pwd_hash = saved.get("pwd_hash", "")
                    st.session_state.logged_in = True
                    st.rerun()
    else:
        reg_id = st.text_input("设置用户ID（唯一，用于区分存档）", key="reg_id")
        reg_pwd = st.text_input("设置密码（至少4位）", type="password", key="reg_pwd")
        reg_pwd2 = st.text_input("确认密码", type="password", key="reg_pwd2")
        import_legacy = False
        if os.path.exists(LEGACY_FILE):
            import_legacy = st.checkbox("导入旧版公共存档（word_data.json）", value=False)
        if st.button("注 册", type="primary", use_container_width=True):
            uid = reg_id.strip()
            if not uid:
                st.error("请输入用户ID！")
            elif load_user_data(uid) is not None:
                st.error("该用户ID已被注册，换一个吧～")
            elif len(reg_pwd) < 4:
                st.error("密码至少4位！")
            elif reg_pwd != reg_pwd2:
                st.error("两次输入的密码不一致！")
            else:
                init_default_session()
                st.session_state.userid = uid
                st.session_state.username = uid
                st.session_state.pwd_hash = hash_pwd(reg_pwd)
                if import_legacy:
                    try:
                        with open(LEGACY_FILE, "r", encoding="utf-8") as f:
                            apply_saved(json.load(f))
                        st.session_state.userid = uid
                    except Exception:
                        pass
                st.session_state.logged_in = True
                save_data()
                st.rerun()

    st.stop()   # ⛔ 未登录时不渲染下面任何功能

# ===================== 单词分类选择 =====================
category = st.selectbox("📚选择单词分类",["小学单词","初中单词","高中单词","四六级单词"])

# ===================== 加载对应词库（修复：合并custom.txt） =====================
def load_words(category_name):
    file_map = {
        "小学单词":"primary.txt",
        "初中单词":"junior.txt",
        "高中单词":"senior.txt",
        "四六级单词":"cet46.txt"
    }
    filename = file_map[category_name]
    word_list = []
    def read_txt(fname):
        res = []
        if not os.path.exists(fname):
            return res
        try:
            with open(fname,"r",encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line and "," in line:
                        en,cn = line.split(",",1)
                        res.append({"word":en.strip(),"meaning":cn.strip()})
        except:
            pass
        return res
    word_list = read_txt(filename)
    # ✅自定义单词改为每个用户独立（存在个人存档里，不再共用 custom.txt）
    word_list += st.session_state.get("custom_words", [])
    return word_list

word_list = load_words(category)

# ===================== 会话数据已由登录流程初始化 =====================
# （登录成功后：init_default_session() + apply_saved() 已填好全部字段）

# ===================== ✅宠物属性定时衰减逻辑 =====================
def pet_decay():
    now_ts = datetime.now().timestamp()
    last_ts = st.session_state.pet_last_decay_time
    delta_hour = (now_ts - last_ts) / 3600
    if delta_hour < 0.01:
        return
    lose_hunger = delta_hour * 10
    lose_happy = delta_hour * 5
    st.session_state.pet["hunger"] = max(0, st.session_state.pet["hunger"] - lose_hunger)
    st.session_state.pet["happiness"] = max(0, st.session_state.pet["happiness"] - lose_happy)
    st.session_state.pet_last_decay_time = now_ts
    save_data()

def reset_pet_temp_image():
    now_ts = datetime.now().timestamp()
    if st.session_state.pet_temp_image and now_ts >= st.session_state.pet_temp_until:
        st.session_state.pet_temp_image = None
        st.session_state.pet_temp_until = 0
        save_data()

pet_decay()
reset_pet_temp_image()

# ===================== 跨天重置今日拼写记录 + 奖励标记 =====================
today_str = str(date.today())
if str(st.session_state.spell_date) != today_str:
    st.session_state.spell_date = date.today()
    st.session_state.today_spell_record = []
    st.session_state.spell_bonus_got = False
    save_data()

# ===================== 词库位置记忆 =====================
if "current_index" not in st.session_state:
    st.session_state.current_index = st.session_state.last_index[category]
if st.session_state.current_index >= len(word_list) and len(word_list)>0:
    st.session_state.current_index = len(word_list)-1

if "show_mean" not in st.session_state:
    st.session_state.show_mean = False
if "shuffle" not in st.session_state:
    st.session_state.shuffle = False
if "shuffled_list" not in st.session_state:
    st.session_state.shuffled_list = []
if "spell_mode" not in st.session_state:
    st.session_state.spell_mode = "关闭拼写自测"

if "prev_cat" not in st.session_state:
    st.session_state.prev_cat = category
if st.session_state.prev_cat != category:
    st.session_state.last_index[st.session_state.prev_cat] = st.session_state.current_index
    st.session_state.current_index = st.session_state.last_index[category]
    st.session_state.show_mean = False
    st.session_state.shuffled_list = []
    st.session_state.prev_cat = category

# ===================== 回调函数 =====================
def save_and_rerun():
    save_data()
    st.rerun()

def show_meaning():
    st.session_state.show_mean = True

def next_word():
    lst = st.session_state.shuffled_list if st.session_state.shuffle and st.session_state.shuffled_list else word_list
    st.session_state.current_index +=1
    st.session_state.show_mean = False
    if st.session_state.current_index >= len(lst):
        st.session_state.current_index = 0
    save_data()

def prev_word():
    lst = st.session_state.shuffled_list if st.session_state.shuffle and st.session_state.shuffled_list else word_list
    st.session_state.current_index -=1
    st.session_state.show_mean = False
    if st.session_state.current_index <0:
        st.session_state.current_index = len(lst)-1
    save_data()

def reset_all():
    st.session_state.current_index = 0
    st.session_state.show_mean = False
    st.session_state.marked = dict()
    st.session_state.wrong_words = []
    st.session_state.daily_count = 0
    st.session_state.focus_start = None
    st.session_state.focus_target_min = None
    st.session_state.spell_bonus_got = False
    save_and_rerun()

def mark_know(word):
    w = word["word"]
    if st.session_state.marked.get(w) == "unknown":
        st.session_state.wrong_words = [i for i in st.session_state.wrong_words if i["word"] != w]
    st.session_state.marked[w] = "know"
    st.session_state.daily_count +=1
    check_achievement()
    next_word()

def mark_unknown(word):
    w = word["word"]
    st.session_state.marked[w] = "unknown"
    exist = any(x["word"] == w for x in st.session_state.wrong_words)
    if not exist:
        st.session_state.wrong_words.append(word)
    st.session_state.daily_count +=1
    check_achievement()
    next_word()

def skip_word():
    next_word()

def do_checkin():
    # ✅打卡条件：今日拼写正确>=10个
    if len(st.session_state.today_spell_record) >= 10:
        st.session_state.checkin_date = date.today()
        check_achievement()
        save_data()
        return True, "✅打卡成功！今天拼写答对够10个单词啦！"
    else:
        return False, f"❌打卡失败！今日拼写正确单词：{len(st.session_state.today_spell_record)} /10"

def remove_one_wrong(idx):
    del st.session_state.wrong_words[idx]
    save_and_rerun()

def toggle_shuffle():
    st.session_state.shuffle = not st.session_state.shuffle
    if st.session_state.shuffle:
        tmp = word_list.copy()
        random.shuffle(tmp)
        st.session_state.shuffled_list = tmp
        st.session_state.current_index =0
    else:
        st.session_state.shuffled_list = []
        st.session_state.current_index =0
    save_and_rerun()

def check_achievement():
    if "首次打卡" not in st.session_state.achievements and st.session_state.checkin_date:
        st.session_state.achievements.append("首次打卡")
    if st.session_state.daily_count >=50 and "单日50词" not in st.session_state.achievements:
        st.session_state.achievements.append("单日50词")
    if st.session_state.daily_count >=50 and "单日突破50词" not in st.session_state.achievements:
        st.session_state.achievements.append("单日突破50词")
    if st.session_state.points >= 10 and "积分新手" not in st.session_state.achievements:
        st.session_state.achievements.append("积分新手")
    if st.session_state.points >= 100 and "积分达人" not in st.session_state.achievements:
        st.session_state.achievements.append("积分达人")
    save_data()

def export_wrong():
    txt = "\n".join([f"{x['word']},{x['meaning']}" for x in st.session_state.wrong_words])
    st.download_button("📥导出错题", data=txt, file_name="wrong_words.txt", mime="text/plain")

def import_wrong(uploaded):
    if uploaded is not None:
        lines = uploaded.read().decode("utf-8").splitlines()
        for l in lines:
            l = l.strip()
            if l and "," in l:
                en,cn = l.split(",",1)
                item = {"word":en.strip(),"meaning":cn.strip()}
                if not any(i["word"]==en.strip() for i in st.session_state.wrong_words):
                    st.session_state.wrong_words.append(item)
        save_and_rerun()

def start_focus(minutes):
    st.session_state.focus_start = datetime.now()
    st.session_state.focus_target_min = minutes

def show_pet_image(image_key, width=280):
    path = PET_IMAGES.get(image_key, PET_IMAGES["cat_base"])
    if os.path.exists(path):
        st.image(path, width=width)
    else:
        st.markdown("<div style='text-align:center;font-size:80px;'>🐱</div>",unsafe_allow_html=True)

# 获取当前穿戴的图片key（只取最后一件）
def get_float_pet_imgkey():
    if st.session_state.pet_temp_image:
        return st.session_state.pet_temp_image
    equipped = st.session_state.pet.get("equipped", [])
    if equipped:
        last_id = equipped[-1]
        item = next((x for x in st.session_state.backpack if x["id"] == last_id), None)
        if item:
            return item["image"]
    return "cat_base"

# ===================== 商城商品 =====================
SHOP_ITEMS = [
    {
        "id":"fish",
        "name":"小鱼干",
        "price":2,
        "type":"food_once",
        "image":"cat_fish",
        "desc":"一次性消耗品，饱食度+5，可重复购买",
        "once_use":True,
        "hunger_add":5
    },
    {
        "id":"can",
        "name":"猫罐头",
        "price":15,
        "type":"food_once",
        "image":"cat_can",
        "desc":"一次性消耗品，饱食度+50，可重复购买",
        "once_use":True,
        "hunger_add":50
    },
    {
        "id":"teaser",
        "name":"逗猫棒",
        "price":15,
        "type":"toy_limit",
        "image":"cat_teaser",
        "desc":"可用10次，用完消失，快乐度+25",
        "max_use":10,
        "happiness_add":25
    },
    {
        "id":"bow",
        "name":"蝴蝶结",
        "price":20,
        "type":"clothes_perm",
        "image":"cat_bow",
        "desc":"永久装饰品，限购1件，可以穿戴",
        "once_use":False,
        "limit_one":True
    },
    {
        "id":"sweater",
        "name":"小毛衣",
        "price":50,
        "type":"clothes_perm",
        "image":"cat_sweater",
        "desc":"永久衣服，限购1件，可以穿戴",
        "once_use":False,
        "limit_one":True
    },
    {
        "id":"crown",
        "name":"皇冠",
        "price":100,
        "type":"clothes_perm",
        "image":"cat_crown",
        "desc":"永久皇冠，限购1件，可以穿戴",
        "once_use":False,
        "limit_one":True
    },
]

# ===================== 购买逻辑 =====================
def buy_item(shop_item):
    item_id = shop_item["id"]
    if shop_item.get("limit_one",False):
        exist = any(bp["id"] == item_id for bp in st.session_state.backpack)
        if exist:
            return False, "❌该物品限购1件，你已经拥有！"
    if st.session_state.points < shop_item["price"]:
        return False, "❌积分不足！"

    st.session_state.points -= shop_item["price"]
    found_idx = None
    for idx,bp in enumerate(st.session_state.backpack):
        if bp["id"] == item_id:
            found_idx = idx
            break
    if found_idx is not None:
        bp_item = st.session_state.backpack[found_idx]
        if shop_item["type"] == "food_once":
            if "count" not in bp_item:
                bp_item["count"] = 0
            bp_item["count"] += 1
        elif shop_item["type"] == "toy_limit":
            bp_item["remain_use"] = shop_item["max_use"]
    else:
        new_bp = {
            "id": shop_item["id"],
            "name": shop_item["name"],
            "type": shop_item["type"],
            "image": shop_item["image"],
        }
        if shop_item["type"] == "food_once":
            new_bp["count"] = 1
        elif shop_item["type"] == "toy_limit":
            new_bp["remain_use"] = shop_item["max_use"]
        st.session_state.backpack.append(new_bp)
    check_achievement()
    save_data()
    return True, "✅购买成功！"

# ===================== 使用物品逻辑 ✅逗猫棒临时图片 =====================
def use_backpack_item(bp_idx):
    bp_item = st.session_state.backpack[bp_idx]
    item_id = bp_item["id"]
    shop_item = next((x for x in SHOP_ITEMS if x["id"] == item_id), None)
    if not shop_item:
        return "❌找不到商品信息"

    if bp_item["type"] == "food_once":
        add_h = shop_item["hunger_add"]
        st.session_state.pet["hunger"] = min(100, st.session_state.pet["hunger"] + add_h)
        # 设置临时图片 + 5秒过期
        if bp_item["id"] == "fish":
            st.session_state.pet_temp_image = "cat_fish"
        elif bp_item["id"] == "can":
            st.session_state.pet_temp_image = "cat_can"
        else:
            st.session_state.pet_temp_image = "cat_fish"
        st.session_state.pet_temp_until = datetime.now().timestamp() + 5

        if "count" not in bp_item:
            bp_item["count"] = 1
        bp_item["count"] -=1
        if bp_item["count"] <=0:
            del st.session_state.backpack[bp_idx]
        msg = f"✅喂食成功！饱食度 +{add_h}"
    elif bp_item["type"] == "toy_limit":
        add_happy = shop_item["happiness_add"]
        st.session_state.pet["happiness"] = min(100, st.session_state.pet["happiness"] + add_happy)
        # ✅逗猫棒临时展示图片
        st.session_state.pet_temp_image = "cat_teaser"
        st.session_state.pet_temp_until = datetime.now().timestamp() + 5

        bp_item["remain_use"] -=1
        if bp_item["remain_use"] <=0:
            del st.session_state.backpack[bp_idx]
            msg = f"✅玩耍成功！快乐度 +{add_happy}，逗猫棒次数用完消失了！"
        else:
            msg = f"✅玩耍成功！快乐度 +{add_happy}，剩余次数：{bp_item['remain_use']}"
    else:
        msg = "这个物品不能直接使用，请去穿戴！"
    save_data()
    return msg

# ===================== 菜单 =====================
menu = st.radio("功能选择",[
    "📖背单词","📒错题本","🔁刷错题模式","📊统计面板",
    "🔍单词搜索","✏️新增单词","🏅成就","💰积分商城","🐱我的宠物","⚙️设置"
],horizontal=True)

# ===================== 背单词页面 =====================
if menu == "📖背单词":
    if len(word_list)==0:
        st.warning("当前词库为空，请检查txt文件！")
    else:
        lst = st.session_state.shuffled_list if st.session_state.shuffle and st.session_state.shuffled_list else word_list
        if st.session_state.current_index >= len(lst):
            st.session_state.current_index =0
        current_word = lst[st.session_state.current_index]
        w_text = current_word["word"]
        w_meaning = current_word["meaning"]
        total = len(lst)
        now = st.session_state.current_index+1
        st.write(f"📌进度：{now}/{total}")
        st.progress(now/total)

        st.checkbox("🔀开启随机乱序",value=st.session_state.shuffle,on_change=toggle_shuffle)

        col_t1,col_t2 = st.columns(2)
        with col_t1:
            focus_min_input = st.number_input("⏱️专注时长(分钟)",min_value=1,max_value=120,value=10)
        with col_t2:
            st.button("▶️开始专注",on_click=start_focus,args=(focus_min_input,))

        if st.session_state.focus_start is not None:
            target_sec = st.session_state.focus_target_min * 60
            start_ts = int(st.session_state.focus_start.timestamp() *1000)
            html_timer = f'''
            <div style="padding:12px;background:#e8f4ff;border-radius:12px;margin:10px 0;">
                <span id="timer-display" style="font-size:18px;font-weight:bold;"></span>
            </div>
            <script>
            const startTs = {start_ts};
            const targetSec = {target_sec};
            function updateTimer(){{
                const nowTs = Date.now();
                const elapsedMs = nowTs - startTs;
                const remainingSec = Math.ceil(targetSec - elapsedMs /1000);
                const el = document.getElementById("timer-display");
                if(remainingSec <=0){{
                    el.innerText = "⏰专注时间结束！";
                    el.style.color = "red";
                }}else{{
                    const m = String(Math.floor(remainingSec /60)).padStart(2,"0");
                    const s = String(remainingSec %60).padStart(2,"0");
                    el.innerText = `⏳剩余时间：${{m}}分${{s}}秒`;
                }}
            }}
            updateTimer();
            setInterval(updateTimer, 1000);
            </script>
            '''
            st.components.v1.html(html_timer, height=80)

        st.session_state.spell_mode = st.radio("📝拼写自测模式",["关闭拼写自测","开启拼写自测"],horizontal=True)

        if st.session_state.spell_mode == "开启拼写自测":
            card_content = f"""
            <div class="word-card">
                <div class="cn-mean">{w_meaning}</div>
                <div class="hide-text">❓请写出对应的英文单词</div>
            </div>
            """
        else:
            card_content = f"""
            <div class="word-card">
                <div class="en-word">{current_word['word']}</div>
                {f'<div class="cn-mean">{current_word["meaning"]}</div>' if st.session_state.show_mean else '<div class="hide-text">❓点击查看释义</div>'}
            </div>
            """
        with st.container():
            st.markdown(card_content,unsafe_allow_html=True)

        speak_js = f"""
        <script>
        const utter = new SpeechSynthesisUtterance("{current_word['word']}");
        utter.lang='en-US';
        speechSynthesis.speak(utter);
        </script>
        """
        if st.button("🔊播放发音"):
            st.components.v1.html(speak_js,height=0)

        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown('<div class="btn-pink">',unsafe_allow_html=True)
            st.button("👀查看释义",on_click=show_meaning)
            st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-pink">',unsafe_allow_html=True)
            st.button("⬅️上一个",on_click=prev_word)
            st.markdown('</div>',unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="btn-pink">',unsafe_allow_html=True)
            st.button("➡️下一个",on_click=next_word)
            st.markdown('</div>',unsafe_allow_html=True)

        st.divider()
        st.subheader("💡掌握标记")
        col_k,col_u,col_s = st.columns(3)
        with col_k:
            st.markdown('<div class="btn-green">',unsafe_allow_html=True)
            st.button("✅我记住啦！",on_click=mark_know,args=(current_word,))
            st.markdown('</div>',unsafe_allow_html=True)
        with col_u:
            st.markdown('<div class="btn-red">',unsafe_allow_html=True)
            st.button("❌还不会",on_click=mark_unknown,args=(current_word,))
            st.markdown('</div>',unsafe_allow_html=True)
        with col_s:
            st.markdown('<div class="btn-pink">',unsafe_allow_html=True)
            st.button("⏭️跳过",on_click=skip_word)
            st.markdown('</div>',unsafe_allow_html=True)

        st.divider()
        bubble_text = ""
        if st.session_state.spell_mode == "开启拼写自测":
            st.divider()
            user_spell = st.text_input("✍️输入这个单词（英文）：", key="spell_input")
            if st.button("✅提交拼写"):
                if user_spell.strip().lower() == w_text.lower():
                    if w_text.lower() not in [x.lower() for x in st.session_state.today_spell_record]:
                        st.session_state.points += 1
                        st.session_state.today_spell_record.append(w_text)
                        # ✅满10个额外5积分，当天只领一次
                        if len(st.session_state.today_spell_record)>=10 and not st.session_state.spell_bonus_got:
                            st.session_state.points +=5
                            st.session_state.spell_bonus_got = True
                            st.success("🎁达标奖励！拼写答对满10词，额外+5积分！")
                        check_achievement()
                        st.success(f"🎉拼写正确！今日积分 +1，当前积分：{st.session_state.points}")
                    else:
                        st.info(f"✅拼写正确！但这个单词今日已领过积分，当前积分：{st.session_state.points}")
                    bubble_text = random.choice(praise_list)
                else:
                    st.error(f"❌错啦！正确单词：{w_text}")
                    bubble_text = random.choice(comfort_list)
                st.session_state.last_bubble_text = bubble_text
                save_data()

        know_count = sum(1 for v in st.session_state.marked.values() if v=="know")
        unknow_count = sum(1 for v in st.session_state.marked.values() if v=="unknown")
        st.write(f"✅记住单词：{know_count}")
        st.write(f"❌需要复习：{unknow_count}")
        st.write(f"💰当前积分：{st.session_state.points}")
        st.write(f"📝今日拼写正确数量：{len(st.session_state.today_spell_record)}/10（打卡门槛）")

        st.divider()
        st.subheader("✅每日打卡")
        if st.button("📝完成今日打卡"):
            ok,msg = do_checkin()
            if ok:
                st.success(msg)
            else:
                st.warning(msg)
        today = date.today()
        if st.session_state.checkin_date == today:
            st.success(f"🎉{st.session_state.username}今日已打卡 {today}")
        elif st.session_state.checkin_date:
            st.info(f"📅上次打卡：{st.session_state.checkin_date}")
        else:
            st.warning(f"⚠️{st.session_state.username}今日未打卡")
        st.metric(label="✅已经标记单词总数",value=len(st.session_state.marked))

# ===================== 错题本 =====================
elif menu == "📒错题本":
    st.subheader("📒错题本")
    st.write("学会了可以单独移除，也可以导入导出。")
    wrong_words = st.session_state.wrong_words
    if len(wrong_words)==0:
        st.info("📭错题本为空！")
    else:
        st.write(f"📚错题数量：{len(wrong_words)}")
        st.divider()
        for idx,item in enumerate(wrong_words):
            col_text,col_del = st.columns([8,2])
            with col_text:
                st.markdown(f"""
                <div class="wrong-card">
                    <strong>{idx+1}. {item['word']}</strong>　
                    <span>{item['meaning']}</span>
                </div>
                """,unsafe_allow_html=True)
            with col_del:
                st.markdown('<div class="btn-red">',unsafe_allow_html=True)
                st.button("🗑️移除",key=f"del_{idx}",on_click=remove_one_wrong,args=(idx,))
                st.markdown('</div>',unsafe_allow_html=True)
        st.divider()
        export_wrong()
        up = st.file_uploader("📤导入错题txt",type=["txt"])
        if up:
            import_wrong(up)
        if st.button("🗑️清空全部错题"):
            st.session_state.wrong_words = []
            save_and_rerun()

# ===================== 刷错题模式 =====================
elif menu == "🔁刷错题模式":
    st.subheader("🔁刷错题模式")
    wrong_words = st.session_state.wrong_words
    if len(wrong_words)==0:
        st.info("📭没有错题，先去背单词标记不会的！")
    else:
        if "wrong_idx" not in st.session_state:
            st.session_state.wrong_idx =0
        if st.session_state.wrong_idx >= len(wrong_words):
            st.session_state.wrong_idx =0
        w_item = wrong_words[st.session_state.wrong_idx]
        st.write(f"📌错题进度：{st.session_state.wrong_idx+1}/{len(wrong_words)}")
        with st.container():
            st.markdown(f"""
            <div class="word-card">
                <div class="en-word">{w_item['word']}</div>
                <div class="cn-mean">{w_item['meaning']}</div>
            </div>
            """,unsafe_allow_html=True)
        def next_w():
            st.session_state.wrong_idx +=1
            if st.session_state.wrong_idx >= len(wrong_words):
                st.session_state.wrong_idx =0
            save_data()
        def remove_current_wrong():
            del st.session_state.wrong_words[st.session_state.wrong_idx]
            if st.session_state.wrong_idx >= len(st.session_state.wrong_words) and len(st.session_state.wrong_words)>0:
                st.session_state.wrong_idx = len(st.session_state.wrong_words)-1
            save_and_rerun()
        c1,c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-green">',unsafe_allow_html=True)
            st.button("✅学会啦，移除错题",on_click=remove_current_wrong)
            st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-pink">',unsafe_allow_html=True)
            st.button("➡️下一道错题",on_click=next_w)
            st.markdown('</div>',unsafe_allow_html=True)

# ===================== 统计面板 =====================
elif menu == "📊统计面板":
    st.subheader(f"📊{st.session_state.username}的学习统计")
    know_count = sum(1 for v in st.session_state.marked.values() if v=="know")
    unknow_count = sum(1 for v in st.session_state.marked.values() if v=="unknown")
    total_marked = know_count + unknow_count
    rate = (know_count / total_marked *100) if total_marked>0 else 0
    st.metric("✅已记住单词",know_count)
    st.metric("❌待复习单词",unknow_count)
    st.metric("📈掌握率",f"{rate:.1f}%")
    st.metric("🔥今日学习单词数量",st.session_state.daily_count)
    st.metric("📒错题总数",len(st.session_state.wrong_words))
    st.metric("💰当前积分",st.session_state.points)
    st.metric("📝今日拼写答对",f"{len(st.session_state.today_spell_record)} /10")

# ===================== 单词搜索 =====================
elif menu == "🔍单词搜索":
    st.subheader("🔍单词搜索")
    search_key = st.text_input("输入英文/中文搜索单词")
    if search_key:
        res = []
        for w in word_list:
            if search_key.lower() in w["word"].lower() or search_key in w["meaning"]:
                res.append(w)
        if res:
            st.write(f"✅找到 {len(res)} 个结果")
            for r in res:
                st.markdown(f"**{r['word']}**：{r['meaning']}")
        else:
            st.info("没有找到这个单词！")

# ===================== 新增单词 =====================
elif menu == "✏️新增单词":
    st.subheader("✏️手动新增单词")
    new_en = st.text_input("英文单词")
    new_cn = st.text_input("中文释义")
    if st.button("➕添加"):
        if new_en and new_cn:
            # ✅保存到当前用户的独立词库（随存档保存，仅本人可见）
            st.session_state.custom_words.append(
                {"word": new_en.strip(), "meaning": new_cn.strip()})
            save_data()
            st.success("✅单词已加入你的自定义词库（仅本人可见）！切换词库时会附带这些单词")
        else:
            st.warning("英文和中文都不能为空！")

# ===================== 成就 =====================
elif menu == "🏅成就":
    st.subheader(f"🏅{st.session_state.username}的勋章")
    if len(st.session_state.achievements)==0:
        st.info("还没有勋章，继续加油背单词！")
    else:
        for a in st.session_state.achievements:
            st.success(f"🎖️ {a}")

# ===================== 积分商城 =====================
elif menu == "💰积分商城":
    st.subheader("💰积分商城")
    st.write(f"当前积分：{st.session_state.points}")
    st.divider()

    for shop_item in SHOP_ITEMS:
        col1,col2,col3 = st.columns([1,3,2])
        with col1:
            show_pet_image(shop_item.get("image","cat_base"))
        with col2:
            st.write(f"### {shop_item['name']}")
            st.write(shop_item["desc"])
            st.write(f"💸所需积分：{shop_item['price']}")
        with col3:
            if st.button(f"🛒购买", key=f"buy_{shop_item['id']}"):
                ok,msg = buy_item(shop_item)
                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)
                save_and_rerun()
        st.divider()

# ===================== 🐱我的宠物 =====================
elif menu == "🐱我的宠物":
    @st.fragment(run_every=1)
    def pet_fragment():
        now_ts = datetime.now().timestamp()
        # 自动检查时间，过期清空临时图片
        if st.session_state.pet_temp_image and now_ts >= st.session_state.pet_temp_until:
            st.session_state.pet_temp_image = None
            st.session_state.pet_temp_until = 0
            save_data()

        st.subheader(f"🐱 {st.session_state.pet['name']}")
        equipped = st.session_state.pet.get("equipped", [])

        # 优先临时图片；穿戴只显示最后一件
        if st.session_state.pet_temp_image:
            show_pet_image(st.session_state.pet_temp_image)
        elif equipped:
            last_id = equipped[-1]
            item = next((x for x in st.session_state.backpack if x["id"] == last_id), None)
            if item:
                show_pet_image(item["image"])
        else:
            show_pet_image("cat_base")

        st.divider()
        st.write(f"🍖 饱食度：{st.session_state.pet['hunger']:.1f}")
        st.progress(st.session_state.pet['hunger'] / 100)
        st.write(f"😊 快乐度：{st.session_state.pet['happiness']:.1f}")
        st.progress(st.session_state.pet['happiness'] / 100)

        if st.session_state.pet['hunger'] < 20:
            st.warning("😿小猫饿啦，快喂点吃的！")
        if st.session_state.pet['happiness'] < 20:
            st.warning("😞小猫有点无聊，陪它玩一会吧！")

        st.divider()
        st.subheader("🎒你的物品")
        if len(st.session_state.backpack)==0:
            st.info("背包空空如也，快去积分商城买点东西吧！")
        else:
            food_list = []
            toy_list = []
            clothes_list = []
            for idx,bp in enumerate(st.session_state.backpack):
                if bp["type"] == "food_once":
                    food_list.append((idx,bp))
                elif bp["type"] == "toy_limit":
                    toy_list.append((idx,bp))
                elif bp["type"] == "clothes_perm":
                    clothes_list.append((idx,bp))

            st.markdown("#### 🍖 食物")
            if len(food_list) == 0:
                st.write("暂无食物")
            else:
                for bp_idx,bp_item in food_list:
                    col1,col2,col3 = st.columns([1,3,2])
                    with col1:
                        show_pet_image(bp_item["image"])
                    with col2:
                        st.write(f"### {bp_item['name']}")
                        st.write(f"📦数量：{bp_item.get('count',0)}")
                    with col3:
                        if st.button(f"🍖喂食", key=f"feed_{bp_idx}"):
                            msg = use_backpack_item(bp_idx)
                            st.success(msg)
                            save_data()
                    st.divider()

            st.markdown("#### 🧸 玩具")
            if len(toy_list) == 0:
                st.write("暂无玩具")
            else:
                for bp_idx,bp_item in toy_list:
                    col1,col2,col3 = st.columns([1,3,2])
                    with col1:
                        show_pet_image(bp_item.get("image", "cat_base"))
                    with col2:
                        st.write(f"### {bp_item['name']}")
                        st.write(f"⚡剩余次数：{bp_item['remain_use']}")
                    with col3:
                        if st.button(f"🧸陪小猫玩", key=f"play_{bp_idx}"):
                            msg = use_backpack_item(bp_idx)
                            st.success(msg)
                            save_data()
                    st.divider()

            st.markdown("#### 👗 服饰")
            if len(clothes_list) == 0:
                st.write("暂无服饰")
            else:
                for bp_idx,bp_item in clothes_list:
                    col1,col2,col3 = st.columns([1,3,2])
                    with col1:
                        show_pet_image(bp_item["image"])
                    with col2:
                        st.write(f"### {bp_item['name']}")
                        st.write("✨永久装饰品")
                    with col3:
                        if bp_item["id"] in st.session_state.pet["equipped"]:
                            if st.button(f"🗝️卸下", key=f"unequip_{bp_idx}"):
                                st.session_state.pet["equipped"].remove(bp_item["id"])
                                save_and_rerun()
                        else:
                            if st.button(f"👕穿戴", key=f"equip_{bp_idx}"):
                                # 新穿戴直接覆盖，只保留最后一件
                                st.session_state.pet["equipped"] = [bp_item["id"]]
                                save_and_rerun()
                    st.divider()

        # 修改宠物名字放在最底部
        st.divider()
        st.write("🛠️ 修改宠物名字")
        new_pet_name = st.text_input("宠物名字", value=st.session_state.pet["name"])
        if st.button("💾保存宠物名字"):
            st.session_state.pet["name"] = new_pet_name
            save_and_rerun()

    pet_fragment()

# ===================== 设置 ✅兑换码：我爱中国，300积分 =====================
elif menu == "⚙️设置":
    st.subheader("⚙️系统设置")
    st.divider()
    st.write("👤个人资料")
    st.text_input("用户ID（登录账号，不可修改）", value=st.session_state.userid, disabled=True)
    new_username = st.text_input("昵称", value=st.session_state.username)
    if st.button("💾保存资料"):
        st.session_state.username = new_username
        save_and_rerun()

    st.divider()
    st.subheader("🚪账号")
    st.write(f"当前登录：**{st.session_state.userid}**（存档文件：`user_data/{safe_userid(st.session_state.userid)}.json`）")
    if st.button("🚪退出登录（切换账号）"):
        st.session_state.logged_in = False
        # 清掉本会话数据，避免串档
        for k in ["marked","wrong_words","pet","backpack","achievements","today_spell_record",
                  "custom_words","last_index","current_index","shuffled_list"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.divider()
    st.subheader("🎁兑换码")
    code_input = st.text_input("输入兑换码")
    if st.button("🎫兑换"):
        code = code_input.strip()
        if code == "我爱中国" and code not in st.session_state.used_codes:
            st.session_state.points += 300
            st.session_state.used_codes.append(code)
            check_achievement()
            save_data()
            st.success("✅兑换成功！获得300积分！")
        elif code in st.session_state.used_codes:
            st.warning("❌这个兑换码已经使用过啦！")
        else:
            st.error("❌兑换码无效！")

    st.divider()
    st.subheader("⚠️危险操作")
    st.warning("下面按钮会清空你的学习记录、错题、积分、宠物数据，谨慎操作！")
    if st.button("🗑️重置全部进度（词库位置、标记、错题、积分、宠物）"):
        # 重置session到初始状态
        st.session_state.marked = {}
        st.session_state.wrong_words = []
        st.session_state.checkin_date = None
        st.session_state.last_index = {"小学单词":0,"初中单词":0,"高中单词":0,"四六级单词":0}
        st.session_state.achievements = []
        st.session_state.daily_count = 0
        st.session_state.points = 0
        st.session_state.spell_date = date.today()
        st.session_state.today_spell_record = []
        st.session_state.pet = {
            "name": "小粉猫",
            "hunger": 50,
            "happiness": 50,
            "equipped": []
        }
        st.session_state.backpack = []
        st.session_state.pet_last_decay_time = datetime.now().timestamp()
        st.session_state.pet_temp_image = None
        st.session_state.pet_temp_until = 0
        st.session_state.used_codes = []
        st.session_state.spell_bonus_got = False
        st.session_state.last_bubble_text = "今天也要好好学单词哦🐱"
        st.session_state.current_index = 0
        st.session_state.shuffled_list = []
        st.session_state.shuffle = False
        save_and_rerun()

    st.divider()
    st.subheader("ℹ️关于本系统")
    st.markdown("""
    💖单词背诵打卡系统｜🐱宠物小猫
    功能清单：
    - 多词库背诵、乱序模式、拼写自测
    - 错题本、错题循环复习
    - 学习统计、打卡、成就勋章
    - 积分商城、宠物养成、喂食陪玩换装
    - 自定义单词导入导出、兑换码福利
    """)

# ===================== 🐱可拖拽悬浮宠物（修复版） =====================
# 初始化气泡文字
if "pet_talk" not in st.session_state:
    st.session_state.pet_talk = "今天也要好好学单词哦🥰"

def build_float_pet_html():
    """把当前宠物图片(base64内嵌) + 气泡 组合成悬浮窗HTML"""
    img_key = get_float_pet_imgkey()
    path = PET_IMAGES.get(img_key, PET_IMAGES["cat_base"])
    if os.path.exists(path):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        img_src = f"data:image/{mime};base64,{get_img_base64(path)}"
        pet_inner = f'<img class="float-cat" id="dragCat" src="{img_src}" draggable="false">'
    else:
        # 图片不存在时显示emoji兜底
        pet_inner = ('<div class="float-cat" id="dragCat" '
                     'style="display:flex;align-items:center;justify-content:center;'
                     'font-size:36px;background:#ffe4f1;">🐱</div>')

    bubble_text = st.session_state.get("last_bubble_text", st.session_state.pet_talk)

    return f'''
<style>
#petBox {{
    position: fixed !important;
    bottom: 20px !important;
    right: 20px !important;
    z-index: 999999 !important;
    display: flex !important;
    align-items: flex-end !important;
    gap:6px !important;
    cursor: move !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    touch-action: none;
}}
#petBox.dragging {{ animation: none !important; }}

.pet-bubble {{
    background-color: #ffffff !important;
    border:2px solid #ffc8dd !important;
    border-radius:14px 14px 14px 3px !important;
    padding:6px 9px !important;
    max-width:150px !important;
    font-size:12px !important;
    color:#333 !important;
    box-shadow:0 3px 10px rgba(0,0,0,0.12) !important;
}}

.float-cat {{
    width:70px !important;
    height:70px !important;
    border-radius:50% !important;
    object-fit: cover !important;
    pointer-events: auto;
    box-shadow:0 4px 12px rgba(214,51,132,0.25) !important;
}}
</style>

<div id="petBox">
    <div class="pet-bubble">{bubble_text}</div>
    {pet_inner}
</div>
'''

# 1) 悬浮窗本体：用 st.markdown 注入主页面DOM（position:fixed 才能悬浮全局）
st.markdown(build_float_pet_html(), unsafe_allow_html=True)

# 2) 拖拽脚本：必须用 components 注入才会真正执行，
#    在iframe里通过 window.parent.document 操作主页面的 #petBox
drag_js = '''
<script>
(function(){
    var doc = window.parent.document;
    var petBox = doc.getElementById("petBox");
    if (!petBox || petBox.dataset.dragInit) return;
    petBox.dataset.dragInit = "1";

    var isDragging = false;
    var offsetX = 0, offsetY = 0;

    function down(e){
        isDragging = true;
        var rect = petBox.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        petBox.style.right = "auto";
        petBox.style.bottom = "auto";
        petBox.classList.add("dragging");
        if (e.cancelable) e.preventDefault();
    }
    function move(e){
        if (!isDragging) return;
        var x = e.clientX - offsetX;
        var y = e.clientY - offsetY;
        var w = doc.documentElement.clientWidth;
        var h = doc.documentElement.clientHeight;
        x = Math.max(0, Math.min(x, w - 60));
        y = Math.max(0, Math.min(y, h - 60));
        petBox.style.left = x + "px";
        petBox.style.top = y + "px";
    }
    function up(){
        if (!isDragging) return;
        isDragging = false;
        petBox.classList.remove("dragging");
    }

    petBox.addEventListener("mousedown", down);
    doc.addEventListener("mousemove", move);
    doc.addEventListener("mouseup", up);

    // 手机/平板触摸拖拽
    petBox.addEventListener("touchstart", function(e){ down(e.touches[0]); }, {passive:true});
    doc.addEventListener("touchmove", function(e){
        if (isDragging){ move(e.touches[0]); if (e.cancelable) e.preventDefault(); }
    }, {passive:false});
    doc.addEventListener("touchend", up);
})();
</script>
'''
st.components.v1.html(drag_js, height=0)
