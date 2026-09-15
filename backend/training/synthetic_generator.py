import os
import cv2
import numpy as np

def generate_dataset_samples(dataset_dir: str = "dataset", count_per_class: int = 4):
    """
    Generates synthetic sample videos into dataset/real and dataset/ai
    to facilitate immediate testing and demonstration of the training pipeline.
    """
    real_dir = os.path.join(dataset_dir, "real")
    ai_dir = os.path.join(dataset_dir, "ai")
    os.makedirs(real_dir, exist_ok=True)
    os.makedirs(ai_dir, exist_ok=True)

    width, height = 320, 240
    fps = 20
    num_frames = 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    print(f"Generating {count_per_class} sample videos for 'real' and 'ai' classes in '{dataset_dir}'...")

    # 1. Generate Real Camera Videos (Natural rigid motion, sensor shot noise, natural color gradients)
    for idx in range(count_per_class):
        filepath = os.path.join(real_dir, f"sample_real_{idx+1}.mp4")
        if os.path.exists(filepath):
            continue

        writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        np.random.seed(100 + idx)
        hue_shift = idx * 30

        for frame_idx in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.float32)
            # Natural sky/ground gradient
            for y in range(height):
                ratio = y / height
                r = (60 + hue_shift) * (1 - ratio) + 150 * ratio
                g = 120 * (1 - ratio) + 110 * ratio
                b = 180 * (1 - ratio) + 70 * ratio
                frame[y, :] = [b % 255, g % 255, r % 255]

            # Rigid panning motion
            pan = int(frame_idx * (2 + idx))
            # Draw rigid physical trees / rectangular objects
            for obj_idx in range(3):
                ox = (obj_idx * 110 - pan) % (width + 60) - 30
                cv2.rectangle(frame, (ox, 120), (ox + 25, 200), (40, 70, 90), -1)
                cv2.circle(frame, (ox + 12, 110), 30, (50, 120, 60), -1)

            # Authentic camera sensor shot noise (Gaussian PRNU-like)
            sensor_noise = np.random.normal(0, 3.5 + idx * 0.5, (height, width, 3))
            noisy = np.clip(frame + sensor_noise, 0, 255).astype(np.uint8)
            writer.write(noisy)

        writer.release()
        print(f"  [+] Created real sample: {os.path.basename(filepath)}")

    # 2. Generate AI-generated Videos (Periodic grid artifacts, non-rigid morphing, unnatural over-smoothing)
    for idx in range(count_per_class):
        filepath = os.path.join(ai_dir, f"sample_ai_{idx+1}.mp4")
        if os.path.exists(filepath):
            continue

        writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        np.random.seed(200 + idx)

        # Upsampling periodic grid artifact (VAE / deconv artifact)
        grid = np.zeros((height, width), dtype=np.float32)
        grid_step = 8 if idx % 2 == 0 else 4
        for y in range(height):
            for x in range(width):
                if (x % grid_step == 0) and (y % grid_step == 0):
                    grid[y, x] = 10.0 + idx * 2.0

        for frame_idx in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.float32)
            # Dreamy over-saturated gradient
            for y in range(height):
                ratio = y / height
                r = 160 * (1 - ratio) + 230 * ratio
                g = 80 * (1 - ratio) + 170 * ratio
                b = 200 * (1 - ratio) + 90 * ratio
                frame[y, :] = [b, g, r]

            # Non-rigid morphing shape (boiling / morphing dynamics)
            radius = int(35 + 10 * np.sin(frame_idx * 0.4 + idx))
            cx = int(width // 2 + 25 * np.cos(frame_idx * 0.3))
            cy = int(height // 2 + 15 * np.sin(frame_idx * 0.25))

            cv2.circle(frame, (cx, cy), radius, (190, 70, 230), -1)

            # Artificial smooth blur
            frame_blur = cv2.GaussianBlur(frame, (5, 5), 0)
            # Latent flicker
            flicker = np.random.normal(0, 1.5, (height, width, 3)).astype(np.float32)
            combined = frame_blur + flicker

            # Inject upsampling grid
            for c in range(3):
                combined[:, :, c] += grid

            final_ai = np.clip(combined, 0, 255).astype(np.uint8)
            writer.write(final_ai)

        writer.release()
        print(f"  [+] Created AI sample: {os.path.basename(filepath)}")

    print("Dataset sample generation complete.")
