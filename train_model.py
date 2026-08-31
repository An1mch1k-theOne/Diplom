import os
import pickle
import warnings
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from implicit.als import AlternatingLeastSquares
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings('ignore')
np.random.seed(42)

DATA_DIR = r"D:\Skillbox_for_VS\python\DIplom\data"
MODELS_DIR = r"D:\Skillbox_for_VS\python\DIplom\models"
os.makedirs(MODELS_DIR, exist_ok=True)

# --- 1. Загрузка данных ---
print("Загрузка events.csv...")
events = pd.read_csv(os.path.join(DATA_DIR, "events.csv"))
events['timestamp'] = pd.to_datetime(events['timestamp'], unit='ms')
events = events.sort_values('timestamp').reset_index(drop=True)
print(f"  Событий: {len(events):,}")

# --- 2. Взвешивание событий ---
WEIGHTS = {'transaction': 5.0, 'addtocart': 3.0, 'view': 1.0}
events['weight'] = events['event'].map(WEIGHTS)

# --- 3. Hold-out split по времени (последняя неделя) ---
max_ts = events['timestamp'].max()
cutoff = max_ts - pd.Timedelta(days=7)
train_events = events[events['timestamp'] <= cutoff]
test_events = events[events['timestamp'] > cutoff]
print(f"  Train: {len(train_events):,}  Test: {len(test_events):,}")
print(f"  Cutoff: {cutoff}  Max: {max_ts}")

# --- 4. Кодирование ID ---
user_enc = LabelEncoder()
item_enc = LabelEncoder()

all_user_ids = pd.concat([train_events['visitorid'], test_events['visitorid']]).unique()
all_item_ids = pd.concat([train_events['itemid'], test_events['itemid']]).unique()

user_enc.fit(all_user_ids)
item_enc.fit(all_item_ids)

train_events = train_events.copy()
train_events['user_idx'] = user_enc.transform(train_events['visitorid'])
train_events['item_idx'] = item_enc.transform(train_events['itemid'])

# --- 5. User-Item матрица ---
n_users = len(user_enc.classes_)
n_items = len(item_enc.classes_)
print(f"  Уникальных пользователей: {n_users:,}")
print(f"  Уникальных товаров: {n_items:,}")

# Агрегация весов
interactions = train_events.groupby(['user_idx', 'item_idx'])['weight'].sum().reset_index()
user_item_matrix = csr_matrix(
    (interactions['weight'].values, (interactions['user_idx'].values, interactions['item_idx'].values)),
    shape=(n_users, n_items)
)
print(f"  Ненулевых элементов: {user_item_matrix.nnz:,}")
print(f"  Плотность: {100 * user_item_matrix.nnz / (n_users * n_items):.4f}%")

# --- 6. Обучение ALS ---
print("\nОбучение ALS модели...")
model = AlternatingLeastSquares(
    factors=100,
    regularization=0.01,
    iterations=30,
    use_gpu=False
)
model.fit(user_item_matrix)
print("  Модель обучена.")

# --- 7. Оценка качества ---
print("\nРасчёт метрик на тестовой выборке...")

test_events_valid = test_events.dropna(subset=['transactionid'])
test_users = test_events_valid['visitorid'].unique()

TOP_K = 10
hit_count = 0
recall_sum = 0.0
ap_sum = 0.0
evaluated = 0

for uid in test_users:
    if uid not in user_enc.classes_:
        continue

    true_items = test_events_valid[test_events_valid['visitorid'] == uid]['itemid'].unique()
    true_items_encoded = []
    for it in true_items:
        if it in item_enc.classes_:
            true_items_encoded.append(item_enc.transform([it])[0])

    if len(true_items_encoded) == 0:
        continue

    user_idx = user_enc.transform([uid])[0]

    try:
        recommendations, _ = model.recommend(user_idx, user_item_matrix[user_idx], N=TOP_K, filter_already_liked_items=True)
    except Exception:
        continue

    rec_set = set(recommendations)
    true_set = set(true_items_encoded)

    hits = rec_set & true_set
    hit_count += int(len(hits) > 0)
    recall_sum += len(hits) / len(true_set)

    ap = 0.0
    hit_count_ap = 0
    for rank, item in enumerate(recommendations, 1):
        if item in true_set:
            hit_count_ap += 1
            ap += hit_count_ap / rank
    ap_sum += ap / min(len(true_set), TOP_K) if len(true_set) > 0 else 0

    evaluated += 1

hit_rate = hit_count / evaluated if evaluated > 0 else 0
recall = recall_sum / evaluated if evaluated > 0 else 0
map_score = ap_sum / evaluated if evaluated > 0 else 0

print(f"  Оценено пользователей: {evaluated}")
print(f"  HitRate@{TOP_K}: {hit_rate:.4f}")
print(f"  Recall@{TOP_K}: {recall:.4f}")
print(f"  MAP@{TOP_K}: {map_score:.4f}")

# --- 8. Сохранение ---
model_path = os.path.join(MODELS_DIR, "model.pkl")
mappings_path = os.path.join(MODELS_DIR, "mappings.pkl")
items_path = os.path.join(MODELS_DIR, "items.pkl")

with open(model_path, 'wb') as f:
    pickle.dump(model, f)

mappings = {
    'user_encoder_classes': user_enc.classes_,
    'item_encoder_classes': item_enc.classes_,
    'user_item_matrix_shape': user_item_matrix.shape,
}
with open(mappings_path, 'wb') as f:
    pickle.dump(mappings, f)

all_items_list = item_enc.classes_.tolist()
with open(items_path, 'wb') as f:
    pickle.dump(all_items_list, f)

print(f"\nСохранено:")
print(f"  Модель: {model_path}")
print(f"  Mappings: {mappings_path}")
print(f"  Items: {items_path}")
print("\nГотово!")
