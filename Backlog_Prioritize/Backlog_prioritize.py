import pandas as pd
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression

from b import backlog  # Import backlog from b.py

def train_and_prioritize(historical_csv_path, backlog_items, additional_historical_df=None):
    """
    Train model using historical data and prioritize backlog items.
    
    Args:
        historical_csv_path: Path to GFG_FINAL.csv (used as fallback if no DB data)
        backlog_items: List of backlog items to prioritize
        additional_historical_df: Optional DataFrame with historical data from database
    
    Data Source Priority:
        1. If additional_historical_df is provided and not empty -> Use ONLY database data
        2. Otherwise -> Use CSV file (GFG_FINAL.csv)
    """
    
    # -------------------------------------------------
    # 1️⃣ Load historical data for training (Database or CSV)
    # -------------------------------------------------
    # Exclusive data source logic: prioritize database data
    if additional_historical_df is not None and not additional_historical_df.empty:
        print(f"[DB DATA] Using database historical data for training: {len(additional_historical_df)} records")
        hist_df = additional_historical_df.copy()
        # Ensure 'name' column exists
        if 'name' not in hist_df.columns and 'summary' in hist_df.columns:
            hist_df['name'] = hist_df['summary']
    else:
        print(f"[CSV FALLBACK] No database data found, using CSV: {historical_csv_path}")
        hist_df = pd.read_csv(historical_csv_path)
        hist_df['name'] = hist_df['summary']
    
    # Normalize historical data
    hist_df['description'] = hist_df['description'].fillna('') if 'description' in hist_df.columns else ''
    hist_df['tags'] = hist_df['tags'].fillna('') if 'tags' in hist_df.columns else ''
    hist_df['full_text'] = hist_df['name'].astype(str) + ". " + hist_df['description'].astype(str) + ". " + hist_df['tags'].astype(str)
    
    # -------------------------------------------------
    # 2️⃣ Load backlog from b.py
    # -------------------------------------------------
    print("Loading backlog from b.py...")
    df = pd.DataFrame(backlog_items)
    df['description'] = df['description'].fillna('')
    df['tags'] = df['tags'].apply(lambda x: ' '.join(x) if isinstance(x, list) else str(x))
    df['full_text'] = df['name'] + ". " + df['description'] + ". " + df['tags']
    
    # -------------------------------------------------
    # 3️⃣ Semantic embeddings model (shared)
    # -------------------------------------------------
    print("Loading AI embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Encode historical data for training
    print("Encoding historical data...")
    hist_embeddings = model.encode(hist_df['full_text'].tolist(), show_progress_bar=True)
    
    # Encode backlog data for prioritization
    print("Encoding backlog data...")
    embeddings = model.encode(df['full_text'].tolist(), show_progress_bar=True)
    
    # -------------------------------------------------
    # 4️⃣ PCA training on historical data
    # -------------------------------------------------
    print("Training PCA on historical data...")
    pca = PCA(n_components=3)
    hist_semantic_features = pca.fit_transform(hist_embeddings)  # Fit on historical
    
    # Transform backlog using trained PCA
    semantic_features = pca.transform(embeddings)  # Transform backlog
    
    scaler = MinMaxScaler(feature_range=(1, 10))
    
    # Scale backlog AI scores
    df['ai_score_1'] = scaler.fit_transform(semantic_features[:, [0]]).flatten()
    df['ai_score_2'] = scaler.fit_transform(semantic_features[:, [1]]).flatten()
    df['ai_score_3'] = scaler.fit_transform(semantic_features[:, [2]]).flatten()
    
    # -------------------------------------------------
    # 5️⃣ Learn coefficients from historical completed rank
    # -------------------------------------------------
    print("Learning weights from historical data...")
    if 'actual_completed_rank' in hist_df.columns:
        train_df = hist_df.dropna(subset=['actual_completed_rank']).copy()
        if len(train_df) > 0:
            train_indices = train_df.index.tolist()
            X = pd.DataFrame({
                's1': hist_semantic_features[train_indices, 0],
                's2': hist_semantic_features[train_indices, 1],
                's3': hist_semantic_features[train_indices, 2],
                'priority': train_df['priority'].map({'high': 3, 'medium': 2, 'low': 1}).fillna(2).values,
                'severity': train_df['severity'].map({
                    'blocker': 5, 'critical': 4, 'major': 3, 'minor': 2, 'trivial': 1
                }).fillna(3).values,
                'is_bug': (train_df['issue_type'] == 'bug').astype(int).values
            })
            y = train_df['actual_completed_rank'].values
            lr = LinearRegression().fit(X, y)
            PRIORITY_COEFF = abs(lr.coef_[3]) if lr.coef_[3] != 0 else 1.0
            SEVERITY_COEFF = abs(lr.coef_[4]) if lr.coef_[4] != 0 else 1.2
            BUG_BOOST = abs(lr.coef_[5]) if lr.coef_[5] != 0 else 1.3
            print(f"Learned coefficients - Priority: {PRIORITY_COEFF:.3f}, Severity: {SEVERITY_COEFF:.3f}, Bug Boost: {BUG_BOOST:.3f}")
        else:
            print("No completed historical data found, using default coefficients...")
            PRIORITY_COEFF, SEVERITY_COEFF, BUG_BOOST = 1.0, 1.2, 1.3
    else:
        print("No 'actual_completed_rank' column, using default coefficients...")
        PRIORITY_COEFF, SEVERITY_COEFF, BUG_BOOST = 1.0, 1.2, 1.3
    
    # Normalize coefficients to reasonable range
    PRIORITY_COEFF = max(0.5, min(2.0, PRIORITY_COEFF))
    SEVERITY_COEFF = max(0.5, min(2.0, SEVERITY_COEFF))
    BUG_BOOST = max(1.0, min(2.0, BUG_BOOST))
    
    # -------------------------------------------------
    # 6️⃣ Weight mappings (apply to backlog)
    # -------------------------------------------------
    priority_map = {'high': 1.0, 'medium': 0.8, 'low': 0.6}
    severity_map = {'blocker': 2.0, 'critical': 1.8, 'major': 1.5, 'minor': 1.1, 'trivial': 0.8}
    
    df['priority_weight'] = df['priority'].map(priority_map).fillna(0.8) * PRIORITY_COEFF
    df['severity_weight'] = df.apply(
        lambda r: severity_map.get(str(r.get('severity')).lower(), 1.0) * SEVERITY_COEFF * BUG_BOOST
        if r['issue_type'] == 'bug' else 1.0,
        axis=1
    )
    
    # -------------------------------------------------
    # 7️⃣ WSJF Calculation
    # -------------------------------------------------
    df['user_value'] = df['ai_score_1'] * df['priority_weight'] * df['severity_weight']
    df['time_criticality'] = df['ai_score_2'] * df['severity_weight']
    df['risk_reduction'] = df['ai_score_3'] * df['severity_weight']
    
    for col in ['user_value', 'time_criticality', 'risk_reduction']:
        df[col] = np.clip(
            MinMaxScaler(feature_range=(1, 10)).fit_transform(df[[col]]).flatten(),
            1, 10
        )
    
    df['cost_of_delay'] = df['user_value'] + df['time_criticality'] + df['risk_reduction']
    df['WSJF'] = df['cost_of_delay'] / df['story_points']
    
    # -------------------------------------------------
    # 8️⃣ MoSCoW via KMeans (trained on combined data for better clustering)
    # -------------------------------------------------
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['ai_cluster'] = kmeans.fit_predict(embeddings)
    
    cluster_wsjf = df.groupby('ai_cluster')['WSJF'].mean().sort_values(ascending=False)
    cluster_map = {
        cluster_wsjf.index[0]: 'Must Have',
        cluster_wsjf.index[1]: 'Should Have',
        cluster_wsjf.index[2]: 'Could Have',
        cluster_wsjf.index[3]: "Won't Have (This Sprint)"
    }
    df['moscow_category'] = df['ai_cluster'].map(cluster_map)
    
    # BUG override
    def bug_moscow_fix(row):
        if row['issue_type'] == 'bug':
            sev = str(row.get('severity')).lower()
            if sev in ['blocker', 'critical', 'major']:
                return 'Must Have'
            elif sev == 'minor':
                return 'Should Have'
            else:
                return 'Could Have'
        return row['moscow_category']
    
    df['moscow_category'] = df.apply(bug_moscow_fix, axis=1)
    
    # -------------------------------------------------
    # 9️⃣ Bug-first ranking
    # -------------------------------------------------
    severity_order = {'blocker': 1, 'critical': 2, 'major': 3, 'minor': 4, 'trivial': 5}
    df['is_bug'] = df['issue_type'] == 'bug'
    df['severity_rank'] = df.apply(
        lambda r: severity_order.get(str(r.get('severity')).lower(), 6) if r['is_bug'] else 99, axis=1
    )
    
    df_sorted = df.sort_values(
        by=['is_bug', 'severity_rank', 'priority_weight', 'WSJF'],
        ascending=[False, True, False, False]
    ).reset_index(drop=True)
    
    df_sorted['priority_rank'] = range(1, len(df_sorted) + 1)
    
    # -------------------------------------------------
    # 10️⃣ Export final prioritized backlog
    # -------------------------------------------------
    df_sorted.to_csv('prioritized_backlog_ai.csv', index=False)
    
    # Generate report
    with open('prioritization_report_ai.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("AI BACKLOG PRIORITIZATION REPORT\n")
        f.write("Trained on: GFG_FINAL.csv | Applied to: b.py backlog\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now()}\n\n")
        f.write(f"Training Data Size: {len(hist_df)} items\n")
        f.write(f"Backlog Size: {len(df)} items\n\n")
        f.write(f"Learned Coefficients:\n")
        f.write(f"  - Priority Weight: {PRIORITY_COEFF:.3f}\n")
        f.write(f"  - Severity Weight: {SEVERITY_COEFF:.3f}\n")
        f.write(f"  - Bug Boost: {BUG_BOOST:.3f}\n\n")
        f.write("-" * 60 + "\n")
        f.write("PRIORITIZED BACKLOG:\n")
        f.write("-" * 60 + "\n")
        for _, r in df_sorted.iterrows():
            f.write(
                f"#{r['priority_rank']:2d} | {r['name'][:50]:<50} | "
                f"Type: {r['issue_type']:<5} | "
                f"WSJF: {r['WSJF']:5.2f} | "
                f"MoSCoW: {r['moscow_category']}\n"
            )
    
    print("\n" + "=" * 60)
    print("PRIORITIZATION COMPLETE!")
    print("=" * 60)
    print(f"Output saved to: prioritized_backlog_ai.csv")
    print(f"Report saved to: prioritization_report_ai.txt")
    print("=" * 60)
    
    return df_sorted


# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    result = train_and_prioritize('GFG_FINAL.csv', backlog)
    print("\n📊 Top 10 Prioritized Items:")
    print(result[['priority_rank', 'name', 'issue_type', 'WSJF', 'moscow_category']].head(10).to_string(index=False))

