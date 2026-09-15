import os
import cv2
import numpy as np

def generate_sample_videos():
    output_dir = os.path.join(os.path.dirname(__file__), "samples")
    os.makedirs(output_dir, exist_ok=True)

    width, height = 640, 360
    fps = 24
    num_frames = 72  # 3 seconds of video

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # -------------------------------------------------------------
    # 1. Authentic Camera Sample
    # Natural scene: smooth camera panning, natural lighting gradient,
    # authentic photon sensor shot noise, physically rigid shapes.
    # -------------------------------------------------------------
    real_path = os.path.join(output_dir, "authentic_camera_sample.mp4")
    print(f"Generating authentic camera video sample at {real_path}...")
    out_real = cv2.VideoWriter(real_path, fourcc, fps, (width, height))

    np.random.seed(42)

    for i in range(num_frames):
        # Base background with natural lighting gradient (sky and terrain)
        frame = np.zeros((height, width, 3), dtype=np.float32)
        
        # Vertical gradient (sky blue to warm ground)
        for y in range(height):
            ratio = y / height
            r = 70 * (1 - ratio) + 160 * ratio
            g = 130 * (1 - ratio) + 120 * ratio
            b = 200 * (1 - ratio) + 80 * ratio
            frame[y, :] = [b, g, r]

        # Natural continuous panning motion
        pan_x = int(i * 3)

        # Draw realistic physical trees/buildings that move with rigid camera motion
        for tree_idx in range(5):
            base_x = (tree_idx * 160 - pan_x) % (width + 100) - 50
            # Trunk
            cv2.rectangle(frame, (base_x + 20, 180), (base_x + 35, 300), (30, 60, 90), -1)
            # Foliage
            cv2.circle(frame, (base_x + 28, 170), 45, (40, 110, 50), -1)

        # Draw a moving authentic car/object
        car_x = int(50 + i * 5)
        cv2.rectangle(frame, (car_x, 260), (car_x + 90, 295), (200, 40, 40), -1)
        cv2.circle(frame, (car_x + 20, 295), 10, (20, 20, 20), -1)
        cv2.circle(frame, (car_x + 70, 295), 10, (20, 20, 20), -1)

        # Realistic camera sensor noise: Gaussian photon noise (PRNU-like)
        # Consistent variance across the entire image
        sensor_noise = np.random.normal(0, 4.0, (height, width, 3))
        noisy_frame = np.clip(frame + sensor_noise, 0, 255).astype(np.uint8)

        out_real.write(noisy_frame)

    out_real.release()
    print("Authentic video sample generated successfully.")

    # -------------------------------------------------------------
    # 2. Synthetic AI-Generated Video Sample
    # Simulates AI video generator (diffusion model):
    # - Periodic high-frequency checkerboard grid pattern (upsampling deconv artifacts)
    # - Non-rigid texture boiling / morphing drift between frames
    # - Spatial over-smoothing (plastic textures lacking natural sensor noise)
    # -------------------------------------------------------------
    ai_path = os.path.join(output_dir, "synthetic_diffusion_sample.mp4")
    print(f"Generating synthetic AI video sample at {ai_path}...")
    out_ai = cv2.VideoWriter(ai_path, fourcc, fps, (width, height))

    # Create periodic 8x8 checkerboard upsampling grid artifact matrix
    grid_pattern = np.zeros((height, width), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            if (x % 8 == 0) and (y % 8 == 0):
                grid_pattern[y, x] = 12.0
            elif (x % 4 == 0) and (y % 4 == 0):
                grid_pattern[y, x] = 6.0

    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.float32)

        # Over-smoothed dreamy background (typical of diffusion prompt)
        for y in range(height):
            ratio = y / height
            r = 140 * (1 - ratio) + 220 * ratio
            g = 90 * (1 - ratio) + 160 * ratio
            b = 180 * (1 - ratio) + 100 * ratio
            frame[y, :] = [b, g, r]

        # Artificial morphing object (shape changes volume / non-rigid boiling drift)
        # In AI video, objects oscillate and deform unnaturally
        radius_warp = int(45 + 12 * np.sin(i * 0.35) + 6 * np.cos(i * 0.7))
        center_x = int(width // 2 + 30 * np.sin(i * 0.2))
        center_y = int(height // 2 + 15 * np.cos(i * 0.25))

        # Synthetic smooth object with unnatural specular shading
        cv2.circle(frame, (center_x, center_y), radius_warp, (180, 80, 220), -1)
        cv2.circle(frame, (center_x - 10, center_y - 10), radius_warp // 2, (230, 160, 255), -1)

        # Realistic morphing tendrils / non-rigid boiling deformation between frames
        for t_idx in range(8):
            angle = (t_idx * 45 + i * 14) * np.pi / 180.0
            length = radius_warp + int(28 * np.sin(i * 0.8 + t_idx * 1.2))
            tx = int(center_x + length * np.cos(angle))
            ty = int(center_y + length * np.sin(angle))
            cv2.line(frame, (center_x, center_y), (tx, ty), (140, 60, 180), 5)

        # 1. First: Smooth dreamy rendering without natural camera sensor noise
        frame_smoothed = cv2.GaussianBlur(frame, (3, 3), 0)

        # 2. Inter-frame texture boiling / latent flicker
        latent_flicker = np.random.normal(0, 1.8, (height, width, 3)).astype(np.float32)
        frame_combined = frame_smoothed + latent_flicker

        # 3. Final latent VAE decoder stage: embed periodic upsampling grid artifacts
        for c in range(3):
            frame_combined[:, :, c] += grid_pattern

        final_ai_frame = np.clip(frame_combined, 0, 255).astype(np.uint8)

        out_ai.write(final_ai_frame)

    out_ai.release()
    print("Synthetic AI video sample generated successfully.")

if __name__ == "__main__":
    generate_sample_videos()
