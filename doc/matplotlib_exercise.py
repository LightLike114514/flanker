import numpy as np
import matplotlib.pyplot as plt


# Model parameters
N0 = 1.0
decay_constant = 0.5

# Discrete sampling for t in [0, 10]
time = np.linspace(0, 10, 500)
particle_number = N0 * np.exp(-decay_constant * time)

# Draw the exponential decay curve
plt.figure(figsize=(8, 5))
plt.plot(
    time,
    particle_number,
    label=r"$N(t)=N_0e^{-\lambda t}$",
    linewidth=2,
)
plt.xlabel("Time $t$")
plt.ylabel("Number of particles $N(t)$")
plt.title("Exponential Decay Curve")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()

# Save a high-resolution image for submission
plt.savefig("exponential_decay.png", dpi=300, bbox_inches="tight")
plt.show()
