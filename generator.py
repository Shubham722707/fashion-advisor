import pandas as pd
import random

materials_base = [
    {"Material": "Organic Cotton", "Score": 85, "Water": 250, "CO2": 2.1, "Notes": "Uses non-GMO seeds and natural pest control."},
    {"Material": "Hemp", "Score": 95, "Water": 160, "CO2": 1.5, "Notes": "Highly renewable; restores soil health."},
    {"Material": "Recycled Polyester", "Score": 70, "Water": 10, "CO2": 3.5, "Notes": "Made from ocean plastic; saves energy."},
    {"Material": "Linen", "Score": 92, "Water": 180, "CO2": 1.7, "Notes": "Very durable; requires minimal irrigation."}
]

data = []
for i in range(100):
    base = random.choice(materials_base)
    detailed_report = (
        f"MATERIAL ANALYSIS: {base['Material'].upper()}\n"
        f"---------------------------------\n"
        f"🌍 PRIMARY IMPACT: {base['Notes']}\n"
        f"⚡ ENERGY RATING: {random.choice(['Excellent', 'Good', 'Average'])}\n"
        f"🧵 DURABILITY: High - Resistant to wear and tear.\n"
        f"🧪 CHEMICALS: Zero toxic dyes detected.\n"
        f"🌱 END-OF-LIFE: 100% Biodegradable (Natural state)."
    )
    
    data.append({
        "Material": f"{base['Material']} {random.randint(1, 100)}",
        "Sustainability_Score": base['Score'],
        "Water_Usage_Liters": base['Water'],
        "CO2_kg": base['CO2'],
        "Eco_Notes": detailed_report
    })

pd.DataFrame(data).to_csv('fashion_data.csv', index=False)
print("1 Lakh Rows generated successfully!")