import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from xgboost import XGBClassifier
import openai

# ==========================================
# 1. Connect to PostgreSQL (pgAdmin)
# ==========================================
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "company"

connection_uri = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(connection_uri)

# ==========================================
# 2. Extract Data directly from PostgreSQL View
# ==========================================
print("Connecting to PostgreSQL and fetching view_churn_features...")

try:
    df = pd.read_sql("SELECT * FROM view_churn_features", con=engine)
    print(f" Successfully loaded dataset with {len(df)} rows!")
    print(f" Columns found: {list(df.columns)}")
except Exception as e:
    print("\n CONNECTION FAILED!")
    print(f"Error Details: {e}")
    exit()

# Safety Check: Stop if dataset has 0 rows
if len(df) == 0:
    print("\n ⚠️ ERROR: 'view_churn_features' returned 0 rows!")
    print("Please run the INSERT query in pgAdmin to add sample data first.")
    exit()

# ==========================================
# 3. Feature Preprocessing
# ==========================================
print("\nPreprocessing features...")

target_col = 'churn_label' if 'churn_label' in df.columns else 'churn'
drop_list = ['customer_id', 'churn_label', 'churn']

# Drop non-feature identifiers
feature_df = df.drop(columns=[col for col in drop_list if col in df.columns])

# Convert text/categorical columns to numeric 0/1 integers
X = pd.get_dummies(feature_df, drop_first=True, dtype=int)
y = df[target_col].astype(int)

print(f" Training matrix prepared: {X.shape[1]} feature columns across {X.shape[0]} rows.")

# ==========================================
# 4. Machine Learning Model Training (XGBoost)
# ==========================================
print("Training XGBoost Classifier...")

model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
model.fit(X.values, y.values)

# Predict Churn Probabilities & assign Risk Levels
df['churn_probability'] = model.predict_proba(X.values)[:, 1]
df['risk_level'] = np.where(df['churn_probability'] >= 0.65, 'High Risk', 
                   np.where(df['churn_probability'] >= 0.35, 'Medium Risk', 'Low Risk'))

if 'is_high_value' not in df.columns:
    df['is_high_value'] = np.where(df.get('monthly_charges', 0) >= 70, 1, 0)

# ==========================================
# 5. Generative AI Retention Engine (OpenAI)
# ==========================================
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"

def generate_retention_strategy(row):
    if row['risk_level'] == 'High Risk' and row.get('is_high_value', 0) == 1:
        if OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
            try:
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                prompt = f"""
                Customer ID: {row.get('customer_id', 'N/A')}
                Monthly Spend: ${row.get('monthly_charges', 'N/A')}
                Churn Risk: {row['churn_probability']*100:.1f}%
                
                Provide a 2-bullet concise retention offer for our customer success team to keep this account.
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=80
                )
                return response.choices[0].message.content.strip()
            except Exception:
                return "Offer 15% discount on annual renewal & priority tech support."
        else:
            return "Offer 15% discount on annual renewal & priority tech support."
    return "Standard retention protocol."

print("Generating AI Retention Strategies...")
df['ai_retention_plan'] = df.apply(generate_retention_strategy, axis=1)

# ==========================================
# 6. Save Predictions Back to PostgreSQL
# ==========================================
export_cols = [c for c in ['customer_id', 'monthly_charges', 'churn_probability', 'risk_level', 'is_high_value', 'ai_retention_plan'] if c in df.columns]
output_df = df[export_cols]

print("Exporting predictions table 'fact_churn_predictions' back to PostgreSQL...")

# Truncate old data safely without dropping table dependencies (prevents view errors)
with engine.begin() as conn:
    conn.exec_driver_sql("TRUNCATE TABLE fact_churn_predictions CASCADE;")

# Append new prediction rows safely
output_df.to_sql('fact_churn_predictions', con=engine, if_exists='append', index=False)

print("\n Success! Pipeline completed and table updated in pgAdmin!")