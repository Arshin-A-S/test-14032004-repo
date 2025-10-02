import matplotlib.pyplot as plt
import numpy as np

# The final, correct metrics from your experiments
final_metrics = {
    "Throughput": 1455850,
    "Latency": 0.69,
    "Accuracy": 96.7,
    "False Positive Rate": 6.1
}

# Create a figure with 3 rows and 1 column of subplots
fig, axes = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [1, 1, 1]})

# --- Chart 1: Throughput ---
ax1 = axes[0]
throughput_val = final_metrics["Throughput"]
ax1.bar("Throughput (requests/sec)", throughput_val, color='#2E86AB', edgecolor='black', width=0.4)
ax1.set_title("System Throughput", fontsize=16, fontweight='bold')
ax1.set_ylabel("Requests / Second", fontsize=12)
ax1.annotate(f'{throughput_val:,.0f}', xy=(0, throughput_val), xytext=(0, 5),
             textcoords="offset points", ha='center', va='bottom', fontweight='bold', fontsize=14)
ax1.tick_params(axis='x', bottom=False, labelbottom=False)
ax1.grid(axis='y', linestyle='--', alpha=0.7)
ax1.set_ylim(top=throughput_val * 1.2)


# --- Chart 2: Accuracy and False Positive Rate ---
ax2 = axes[1]
acc_fpr_labels = ["Accuracy", "False Positive Rate"]
acc_fpr_values = [final_metrics["Accuracy"], final_metrics["False Positive Rate"]]
bars = ax2.bar(acc_fpr_labels, acc_fpr_values, color=['#F18F01', '#C73E1D'], edgecolor='black', width=0.5)

ax2.set_title("Model Effectiveness", fontsize=16, fontweight='bold')
ax2.set_ylabel("Percentage (%)", fontsize=12)
ax2.set_ylim(0, 110) # Set a fixed 0-110 scale to compare percentages fairly

# Add labels to both bars
for bar in bars:
    height = bar.get_height()
    ax2.annotate(f'{height:.1f}%',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3), # 3 points vertical offset
                 textcoords="offset points",
                 ha='center', va='bottom', fontweight='bold', fontsize=14)
ax2.grid(axis='y', linestyle='--', alpha=0.7)


# --- Chart 3: Latency ---
ax3 = axes[2]
latency_val = final_metrics["Latency"]
ax3.bar("Latency (microseconds)", latency_val, color='#A23B72', edgecolor='black', width=0.4)
ax3.set_title("Scoring Latency", fontsize=16, fontweight='bold')
ax3.set_ylabel("Microseconds", fontsize=12)
ax3.annotate(f'{latency_val:.2f}', xy=(0, latency_val), xytext=(0, 5),
             textcoords="offset points", ha='center', va='bottom', fontweight='bold', fontsize=14)
ax3.tick_params(axis='x', bottom=False, labelbottom=False)
ax3.grid(axis='y', linestyle='--', alpha=0.7)
ax3.set_ylim(top=latency_val * 1.5)


# Add a main title for the entire figure and adjust layout
fig.suptitle('Final Federated Learning Performance Metrics', fontsize=20, fontweight='bold')
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# Save the final chart
plt.savefig('final_performance_metrics_grouped_chart.png', dpi=300)

print("Grouped chart saved successfully as 'final_performance_metrics_grouped_chart.png'")