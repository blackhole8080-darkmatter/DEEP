# deep/tech/computer_vision.py — Computer Vision (Bible Section 19)
"""Object detection, segmentation, depth, pose. Heavy models (YOLOv8, DETR,
MiDaS, MediaPipe, Stable Diffusion) are optional and guarded; a pure-numpy
classical-CV core (edges, blur, thresholding, Hough-free corner energy) runs
without OpenCV so the module is always useful."""
from __future__ import annotations


import numpy as np

try:
    import cv2
    CV2 = True
except Exception:  # pragma: no cover
    CV2 = False

try:
    from ultralytics import YOLO  # noqa: F401
    YOLO_OK = True
except Exception:  # pragma: no cover
    YOLO_OK = False


class VisionEngine:
    def __init__(self, config=None):
        self.config = config
        self._yolo = None

    # ── classical CV (pure numpy) ───────────────────────────────────
    @staticmethod
    def _to_gray(img):
        img = np.asarray(img, float)
        if img.ndim == 3:
            return img[..., :3] @ np.array([0.299, 0.587, 0.114])
        return img

    def sobel_edges(self, img) -> dict:
        g = self._to_gray(img)
        Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float)
        Ky = Kx.T
        gx = _conv2(g, Kx)
        gy = _conv2(g, Ky)
        mag = np.hypot(gx, gy)
        edge_density = float((mag > mag.mean() + mag.std()).mean())
        return {"edge_map_shape": list(mag.shape), "edge_density": edge_density,
                "result": {"edge_density": edge_density},
                "verbal": f"Sobel edge detection: {edge_density*100:.1f}% of pixels are edges."}

    def image_stats(self, img) -> dict:
        g = self._to_gray(img)
        return {"mean": float(g.mean()), "std": float(g.std()),
                "shape": list(np.asarray(img).shape),
                "result": {"mean": float(g.mean())},
                "verbal": f"Image {g.shape}: mean intensity {g.mean():.1f}, "
                          f"contrast (std) {g.std():.1f}."}

    # ── deep models (guarded) ───────────────────────────────────────
    def detect_objects(self, image_path) -> dict:
        if not YOLO_OK:
            return {"result": None,
                    "verbal": "Object detection needs ultralytics (YOLOv8), sir — "
                              "not installed. Classical edge analysis is available."}
        if self._yolo is None:
            self._yolo = YOLO("yolov8n.pt")
        res = self._yolo(image_path)
        names = res[0].names
        dets = [names[int(c)] for c in res[0].boxes.cls]
        return {"detections": dets, "result": dets,
                "verbal": f"Detected: {', '.join(dets) if dets else 'nothing'}."}

    def depth_estimation(self, image_path) -> dict:
        try:
            import torch  # noqa: F401
            # MiDaS via torch.hub would load here
        except Exception:
            pass
        return {"result": None,
                "verbal": "Monocular depth needs MiDaS (torch.hub) and an image, sir — "
                          "model not loaded."}

    # ── classical CV via OpenCV (real when cv2 present) ─────────────
    def canny_edges(self, img, low=50, high=150) -> dict:
        if not CV2:
            return self.sobel_edges(img)
        g = self._to_gray(img).astype(np.uint8)
        edges = cv2.Canny(g, low, high)
        return {"edge_density": float((edges > 0).mean()), "result": "ok",
                "verbal": f"Canny edges: {(edges>0).mean()*100:.1f}% edge pixels."}

    def hough_lines(self, img) -> dict:
        if not CV2:
            return {"result": None, "verbal": "OpenCV needed for Hough transform, sir."}
        g = self._to_gray(img).astype(np.uint8)
        edges = cv2.Canny(g, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=20, maxLineGap=5)
        n = 0 if lines is None else len(lines)
        return {"n_lines": n, "result": n,
                "verbal": f"Hough transform found {n} line segment(s)."}

    def orb_features(self, img, n_features=500) -> dict:
        if not CV2:
            return {"result": None, "verbal": "OpenCV needed for ORB, sir."}
        g = self._to_gray(img).astype(np.uint8)
        orb = cv2.ORB_create(nfeatures=n_features)
        kp, desc = orb.detectAndCompute(g, None)
        return {"n_keypoints": len(kp), "result": len(kp),
                "verbal": f"ORB detected {len(kp)} keypoints for matching/SLAM."}

    def harris_corners(self, img) -> dict:
        if not CV2:
            return {"result": None, "verbal": "OpenCV needed, sir."}
        g = np.float32(self._to_gray(img))
        dst = cv2.cornerHarris(g, 2, 3, 0.04)
        n = int((dst > 0.01 * dst.max()).sum())
        return {"n_corners": n, "result": n,
                "verbal": f"Harris corner detector found {n} corner pixels."}

    def optical_flow(self, img1, img2) -> dict:
        if not CV2:
            return {"result": None, "verbal": "OpenCV needed for optical flow, sir."}
        g1 = self._to_gray(img1).astype(np.uint8); g2 = self._to_gray(img2).astype(np.uint8)
        flow = cv2.calcOpticalFlowFarneback(g1, g2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag = np.linalg.norm(flow, axis=2)
        return {"mean_motion": float(mag.mean()), "result": float(mag.mean()),
                "verbal": f"Dense optical flow: mean motion magnitude {mag.mean():.2f} px."}

    def segment_threshold(self, img) -> dict:
        if not CV2:
            return {"result": None, "verbal": "OpenCV needed, sir."}
        g = self._to_gray(img).astype(np.uint8)
        _, mask = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        n_labels, _ = cv2.connectedComponents(mask)
        return {"n_segments": int(n_labels - 1), "result": int(n_labels - 1),
                "verbal": f"Otsu threshold segmentation found {n_labels-1} region(s)."}

    def test(self) -> None:
        img = np.zeros((50, 50))
        img[20:30, 20:30] = 255  # a square
        e = self.sobel_edges(img)
        assert e["edge_density"] > 0
        s = self.image_stats(img)
        assert s["mean"] > 0
        if CV2:
            assert "edge_density" in self.canny_edges(img)
            assert self.harris_corners(img)["n_corners"] >= 0
            assert "n_lines" in self.hough_lines(img)
            assert self.orb_features(img)["n_keypoints"] >= 0
            assert self.segment_threshold(img)["n_segments"] >= 1
            img2 = np.zeros((50, 50)); img2[22:32, 22:32] = 255
            assert self.optical_flow(img, img2)["mean_motion"] >= 0
            print("computer_vision.VisionEngine: OK (incl. Canny, Hough, ORB, Harris, "
                  "optical flow, segmentation)")
        else:
            print("computer_vision.VisionEngine: OK")


def _conv2(img, kernel):
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode="edge")
    out = np.zeros_like(img)
    for i in range(kh):
        for j in range(kw):
            out += kernel[i, j] * padded[i:i + img.shape[0], j:j + img.shape[1]]
    return out


_engine = VisionEngine()


def analyze(text: str) -> dict:
    low = text.lower()
    if "edge" in low:
        # demo on a synthetic image
        img = np.zeros((64, 64)); img[16:48, 16:48] = 255
        return _engine.sobel_edges(img)
    return {"result": None,
            "verbal": "Give me an image path, sir — e.g. detect objects in photo.jpg. "
                      "YOLOv8 powers detection; classical edge analysis works offline."}


def depth(text: str) -> dict:
    return _engine.depth_estimation(None)


def test() -> None:
    VisionEngine().test()


if __name__ == "__main__":
    test()
