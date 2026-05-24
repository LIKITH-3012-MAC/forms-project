# AI Payment Receipt Analysis System — Complete A to Z Technical Documentation
## SAKRA VISION Event Registration Platform
### Developer: Likith Naidu Anumakonda

> **Generated on:** May 24, 2026  
> **Project Root Path:** `/Users/likithnaidu/Desktop/forms-project`  
> **Current Model Version:** `multi-stage-v1` (Calibrated SVM_RBF + PyTesseract OCR Fusion)  
> **Current Deployment Architecture:** FastAPI Python Backend (Render) + Vercel HTML/JS Frontend  
> **Generated From:** Actual current project implementation and trained model artifacts.

---

## Telugu-to-English Quick Reference Table
Before we dive into the deep learning architectures, here is a quick mapping of key machine learning terms into conversational Telugu + English to help you build instant intuition:

| English Term | Telugu Explanation | Simple Analogous Meaning |
| :--- | :--- | :--- |
| **Convolutional Neural Network (CNN)** | ఇమేజ్ లోని ప్యాటర్న్స్ (అంచులు, షేప్స్) ని గుర్తించే ఒక నెట్వర్క్. | కంటి చూపుతో ఒక ఆబ్జెక్ట్ ని గుర్తుపట్టే విధానం. |
| **Transfer Learning** | ఆల్రెడీ ట్రైన్ అయిన పెద్ద మోడల్ ని మన చిన్న టాస్క్ కోసం వాడుకోవడం. | కార్ డ్రైవింగ్ వచ్చిన వ్యక్తి ఈజీగా బస్ డ్రైవింగ్ నేర్చుకున్నట్టు. |
| **Data Augmentation** | ఒకే ఇమేజ్ ని రకరకాలుగా మార్చి (తిప్పి, బ్లర్ చేసి) ట్రైనింగ్ డేటా పెంచడం. | ఒకే ఫోటోను ఫిల్టర్లు వేసి 10 రకాలుగా చూపించడం. |
| **Isotonic Calibration** | మోడల్ చెప్పే కాన్ఫిడెన్స్ పర్సంటేజ్ నిజంగా ఎంత నమ్మదగినదో సరిచేయడం. | ఓవర్-కాన్ఫిడెంట్ విద్యార్థికి రియాలిటీ చెక్ పెట్టి మార్కులు అంచనా వేయడం. |
| **Feature Extraction** | ఇమేజ్ లోని ముఖ్యమైన సమాచారాన్ని నెంబర్ల రూపంలోకి మార్చడం. | పెద్ద బుక్ లోని ముఖ్యాంశాలను షార్ట్-నోట్స్ రాయడం. |

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Why AI Receipt Similarity Is Needed](#3-why-ai-receipt-similarity-is-needed)
4. [Very Important Limitation: AI Does Not Verify Real Payment](#4-very-important-limitation-ai-does-not-verify-real-payment)
5. [Final System Architecture](#5-final-system-architecture)
6. [Complete End-to-End Flow](#6-complete-end-to-end-flow)
7. [Current Folder and File Architecture](#7-current-folder-and-file-architecture)
8. [Libraries Actually Used in This Project](#8-libraries-actually-used-in-this-project)
9. [User Upload Flow in `form.html`](#9-user-upload-flow-in-formhtml)
10. [Frontend Image Preview and AI Score UI](#10-frontend-image-preview-and-ai-score-ui)
11. [Frontend to Backend API Request Flow](#11-frontend-to-backend-api-request-flow)
12. [FastAPI AI Prediction Endpoint](#12-fastapi-ai-prediction-endpoint)
13. [Image File Validation and Security](#13-image-file-validation-and-security)
14. [Image Preprocessing Pipeline](#14-image-preprocessing-pipeline)
15. [Training Dataset Used](#15-training-dataset-used)
16. [Photos Folder Usage and Labelling](#16-photos-folder-usage-and-labelling)
17. [Positive and Negative Classes](#17-positive-and-negative-classes)
18. [Data Augmentation Explained Deeply](#18-data-augmentation-explained-deeply)
19. [Transfer Learning Explained](#19-transfer-learning-explained)
20. [EfficientNetB0 Explained from Beginner Level](#20-efficientnetb0-explained-from-beginner-level)
21. [Phase 1: Head-Only Training](#21-phase-1-head-only-training)
22. [Phase 2: Fine-Tuning](#22-phase-2-fine-tuning)
23. [Phase 3: Full-Tuning and Early Stopping](#23-phase-3-full-tuning-and-early-stopping)
24. [Feature Extraction Pipeline](#24-feature-extraction-pipeline)
25. [Meaning of 1280 Visual Features](#25-meaning-of-1280-visual-features)
26. [Meaning of 5 Quality Features](#26-meaning-of-5-quality-features)
27. [Meaning of 1285 Fused Features](#27-meaning-of-1285-fused-features)
28. [Machine Learning Classifier Ensemble](#28-machine-learning-classifier-ensemble)
29. [Logistic Regression, SVM, ExtraTrees and GradientBoosting Comparison](#29-logistic-regression-svm-extratrees-and-gradientboosting-comparison)
30. [Why the Final Classifier Was Selected](#30-why-the-final-classifier-was-selected)
31. [Calibration and Why Percentage Can Be Misleading](#31-calibration-and-why-percentage-can-be-misleading)
32. [ONNX File Explained A to Z](#32-onnx-file-explained-a-to-z)
33. [PKL Files Explained A to Z](#33-pkl-files-explained-a-to-z)
34. [Feature Scaler Explained A to Z](#34-feature-scaler-explained-a-to-z)
35. [Model Config and Metrics JSON Explained](#35-model-config-and-metrics-json-explained)
36. [Full Runtime Prediction Flow](#36-full-runtime-prediction-flow)
37. [How One Uploaded Image Becomes a Percentage](#37-how-one-uploaded-image-becomes-a-percentage)
38. [Backend Integration with FastAPI](#38-backend-integration-with-fastapi)
39. [Frontend Display of AI Similarity Score](#39-frontend-display-of-ai-similarity-score)
40. [Database Storage of AI Result, If Implemented](#40-database-storage-of-ai-result-if-implemented)
41. [Admin Manual Verification Flow](#41-admin-manual-verification-flow)
42. [Real-World Testing and Metrics](#42-real-world-testing-and-metrics)
43. [Why 100% Accuracy Must Be Treated Carefully](#43-why-100-accuracy-must-be-treated-carefully)
44. [Previous Human Photo 94% Failure Analysis](#44-previous-human-photo-94-failure-analysis)
45. [How the Retraining Tried to Fix That Problem](#45-how-the-retraining-tried-to-fix-that-problem)
46. [Strict Independent Testing Required](#46-strict-independent-testing-required)
47. [Performance and Render Deployment](#47-performance-and-render-deployment)
48. [Security and Privacy of Receipt Images](#48-security-and-privacy-of-receipt-images)
49. [Debugging Guide](#49-debugging-guide)
50. [How to Add More Training Photos Correctly](#50-how-to-add-more-training-photos-correctly)
51. [How to Retrain the Model Again](#51-how-to-retrain-the-model-again)
52. [How to Export and Deploy the New Model](#52-how-to-export-and-deploy-the-new-model)
53. [Future Accuracy Improvements](#53-future-accuracy-improvements)
54. [Viva / Interview Questions and Answers](#54-viva--interview-questions-and-answers)
55. [One-Minute Product Explanation](#55-one-minute-product-explanation)
56. [Glossary](#56-glossary)
57. [Final Summary](#57-final-summary)

---

## 1. Project Overview
The SAKRA VISION Event Registration Platform is a production-grade, highly secured event registration web application. In this platform, attendees fill out their details, complete a manual fee transfer by scanning a static UPI QR code displayed on the page, and then upload a screenshot of their transaction along with entering their 12-digit transaction ID (UTR reference). 

To streamline administrative review and block malicious submissions immediately, we have designed a **Multi-Stage AI Receipt Validation Pipeline** inside the system. 

```
┌──────────────────────────────────────────────────────────┐
│                   SAKRA VISION SYSTEM                    │
│   ┌───────────────┐     ┌──────────────┐                 │
│   │ User Details  │ ──> │ UPI QR Code  │ ──> User Pays   │
│   └───────────────┘     └──────────────┘                 │
│                                                          │
│   ┌───────────────┐     ┌──────────────┐     ┌─────────┐ │
│   │ Upload Image  │ ──> │ AI Predictor │ ──> │ Submit  │ │
│   └───────────────┘     └──────────────┘     └─────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Problem Statement
Manual event registrations suffer from three massive points of friction:
1. **Malicious Spammers:** Users uploading blank files, memes, random selfies, or landscape photos to bypass registration walls.
2. **Duplicate/Fake Reference IDs:** Users pasting random 12-digit numbers while uploading completely unrelated images.
3. **Transaction Status Verification:** Disentangling pending or failed transaction screenshots from fully successful ones.

Administrators previously had to manually open and review every single registration screenshot, wasting dozens of hours.

---

## 3. Why AI Receipt Similarity Is Needed
AI Receipt Similarity acts as a **smart digital filter**. It provides immediate feedback to the user and protects the backend database from junk uploads. By visually classifying the screenshot at upload time:
- It instantly alerts the user if the uploaded image does not resemble a valid receipt.
- It blocks the submission of obviously fake receipts (like memes or selfies).
- It provides organizers with a pre-validated "AI Similarity Score" on their administrative dashboard, helping them prioritize approvals.

---

## 4. Very Important Limitation: AI Does Not Verify Real Payment

> [!CAUTION]
> **AI Receipt Similarity IS NOT a Payment Gateway!**  
> AI only verifies the **visual resemblance** of the image to a payment screenshot (YOLO or EfficientNet layout features) and checks for textual signals (Tesseract OCR). It does **not** communicate with the bank, it does **not** check if the money has actually arrived in the organizer's account, and it does **not** authenticate the UTR with the UPI network.  
> **Manual admin bank-statement verification remains mandatory.**

---

## 5. Final System Architecture
Here is how the entire multi-stage visual and text check is structured:

```
[ User Selects File ]
         │
         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ STAGE A: Quality Gate (Pillow + NumPy)                    │
 │ ├─ MIME check (JPG, PNG, WEBP)                           │
 │ ├─ File size check (<= 3MB)                              │
 │ ├─ Size dimensions check (w/h >= 50px)                   │
 │ ├─ Laplacian Variance Blur Check (score >= 30.0)         │
 │ └─ Brightness Check (12.0 < score < 253.0)               │
 └──────────────────────────────────────────────────────────┘
         │ (If unacceptable: Reject / Alert User)
         ▼ (If Acceptable)
 ┌──────────────────────────────────────────────────────────┐
 │ STAGE B: Visual Feature Extractor (ONNX EfficientNetB0)  │
 │ ├─ Resize Image to 224 x 224 (Bilinear)                  │
 │ └─ Extract 1280 Visual Embedding Dimensions              │
 └──────────────────────────────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ STAGE C: Quality Feature Fusion                          │
 │ └─ Append [Blur, Brightness, AspectRatio, Width, Height] │
 │    generating 1285 Fused Feature Vector                  │
 └──────────────────────────────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ STAGE D: Scaler & Classifier Ensemble (SKLearn .pkl)      │
 │ ├─ Normalize features with StandardScaler (.pkl)         │
 │ ├─ Run calibrated SVM_RBF Classifier                     │
 │ └─ Apply Isotonic Calibration => Receipt Probability %    │
 └──────────────────────────────────────────────────────────┘
         │
         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ STAGE E: OCR Secondary Verification (PyTesseract OCR)     │
 │ ├─ Search for amount / success / application keywords    │
 │ ├─ Search for date / UPI reference patterns              │
 │ └─ Search for negative "failed/pending" keywords         │
 └──────────────────────────────────────────────────────────┘
         │
         ▼
[ Stage F: Joint Fusion Decision Logic ]
```

---

## 6. Complete End-to-End Flow
1. **User interaction:** User uploads a screenshot.
2. **Quality Check:** Frontend sends the screenshot to the backend where it passes a Pillow/NumPy-based quality check.
3. **ONNX Run:** The image is passed through the ONNX EfficientNetB0 feature extractor, outputting a 1280-dimensional visual array.
4. **Fusion:** Five quality features are appended, forming a 1285-dimensional fused vector.
5. **Inference:** A calibrated SVM RBF model calculates the visual probability of it being a receipt.
6. **OCR Scan:** PyTesseract scans for textual payment success/failure cues.
7. **Joint Gate Decision:** The backend combines visual probability and text presence into a single percentage, returning a status: `likely_receipt`, `needs_review`, `suspicious_or_not_successful`, or `not_receipt`.

---

## 7. Current Folder and File Architecture
The relevant project structure is organized as follows:

```
forms-project/
├── backend/
│   ├── app/
│   │   ├── settings.py           # Contains threshold constants and file paths
│   │   ├── image_validator.py    # Pillow/NumPy quality check (Stage A)
│   │   ├── ocr_analyzer.py       # Tesseract OCR keyword verification (Stage E)
│   │   └── predictor.py          # Loads ONNX/PKL models & coordinates predictions
│   ├── models/
│   │   ├── receipt_feature_extractor.onnx  # ONNX EfficientNetB0 model (~16MB)
│   │   ├── receipt_classifier.pkl          # Trained Calibrated SVM Classifier (~3.5MB)
│   │   ├── feature_scaler.pkl              # StandardScaler checkpoint (~31KB)
│   │   ├── model_config.json               # Details training samples and feature dims
│   │   └── training_metrics.json           # Evaluation metrics of the trained model
│   ├── training/
│   │   ├── grand_retrain.py      # Grand retrain master pipeline (all 3 training phases)
│   │   └── prepare_dataset.py    # Downloads seeds and structures datasets
│   └── main.py                   # FastAPI server entry point and registration router
├── dataset/                      # Local datasets structured into train/val/test splits
└── frontend/
    └── form.html                 # Frontend page containing drag-and-drop & circular UI
```

### Purpose of Core Runtime & Training Files

| File / Folder | Purpose | Used During Training or Runtime? |
| :--- | :--- | :--- |
| `frontend/form.html` | Screenshot drag-and-drop area and animated circular score rendering. | Runtime |
| `backend/main.py` | Hosts FastAPI endpoints (`/api/receipt/predict`, `/api/register`). | Runtime |
| `backend/app/predictor.py` | Orchestrates Stage A, B, C, D, E and produces joint prediction. | Runtime |
| `backend/models/receipt_feature_extractor.onnx` | Pretrained + fine-tuned EfficientNetB0 backbone in ONNX format. | Runtime |
| `backend/models/receipt_classifier.pkl` | Final Scikit-Learn SVM classifier with isotonic calibration Prefit. | Runtime |
| `backend/models/feature_scaler.pkl` | StandardScaler checkpoint used to normalize input features. | Runtime |
| `backend/training/grand_retrain.py` | Master training pipeline. Handles unfreezing and Scikit-Learn search. | Training Only |

---

## 8. Libraries Actually Used in This Project

> [!NOTE]
> **Telugu Meaning:**  
> "ఈ ప్రాజెక్ట్ రన్ అవ్వడానికి మనం వాడిన ముఖ్యాంశ లైబ్రరీలు ఇవే. పిల్లో తో ఇమేజ్ ఓపెన్ చేసి, ONNX తో ఫీచర్స్ తీసి, స్కిట్-లెర్న్ క్లాసిఫైయర్ ద్వారా పర్సంటేజ్ లెక్కిస్తాము."

Here are the libraries configured in `requirements.txt`:
1. **`fastapi` & `uvicorn`:** High-performance async Python backend server.
2. **`pillow` (PIL):** Safe image open, resize, and color mode conversion.
3. **`numpy`:** Vector operations, array concatenation, and variance math.
4. **`onnxruntime`:** Ultra-fast, lightweight framework for running the `.onnx` visual feature extractor.
5. **`joblib`:** Loads `.pkl` binary files (the SVM classifier and features scaler).
6. **`pytesseract`:** Integrates with Tesseract OCR binary to parse textual contents.
7. **`tensorflow` (Training Only):** Used to unfreeze, train, and calibrate the EfficientNetB0 backbone.
8. **`scikit-learn` (Training & Runtime):** Trains the SVM classifier and powers the `StandardScaler`.

---

## 9. User Upload Flow in `form.html`
The frontend implements a premium, interactive user experience:
1. **Interactive Drag & Drop:** Users can drag-and-drop a file onto the `#uploadCard` or click to trigger the hidden file input (`#payment_screenshot`).
2. **MIME/Size Filters:** The JavaScript immediately enforces file-type checks (only `.jpg`, `.jpeg`, `.png`, `.webp`) and verifies that the file size is under **3MB**.
3. **Pillow/ML Pipeline Call:** The moment a valid file is selected, a new `FileReader` renders a preview of the image (`#paymentPreviewImg`) and asynchronously triggers the AI validation pipeline.

---

## 10. Frontend Image Preview and AI Score UI
Once the file is loaded, the `#aiReceiptPanel` unhides. The panel displays:
- **Circular Progress Ring:** The `#aiScoreRing` uses an animated conic gradient powered by a custom CSS property (`--score-angle`) to smoothly draw a circular boundary matching the similarity percentage.
- **Dynamic Color Themes:** The panel's styling adapts dynamically depending on the status returned by the API:
  - `state-high` (Verified - Green): The score is high, showing verified checkmarks.
  - `state-medium` (Needs Review - Orange): Moderate score, indicating review needed.
  - `state-low` (Rejected - Red): Low score, displaying warning badges.

---

## 11. Frontend to Backend API Request Flow
The frontend communicates asynchronously with the backend server via `fetch`:
- **API URL:** `${CONFIG.BACKEND_URL}/api/receipt/predict`
- **Method:** `POST`
- **Payload:** `multipart/form-data` containing the file in a field named `file`.

Here is the exact asynchronous call implemented in `frontend/form.html`:
```javascript
async function analyzeReceiptScreenshot(file) {
  if (!file) return;

  const requestId = ++latestAiRequestId;
  showAiAnalyzingState();

  const aiFormData = new FormData();
  aiFormData.append("file", file);

  try {
    const response = await fetch(`${CONFIG.BACKEND_URL}/api/receipt/predict`, {
      method: "POST",
      body: aiFormData
    });

    const data = await response.json();
    if (requestId !== latestAiRequestId) return; // Prevent race conditions

    if (!response.ok || !data.success || data.status === "model_unavailable") {
      showAiUnavailableState();
      return;
    }

    aiAllowSubmission = data.allow_submission;
    renderAiReceiptScore(data);

  } catch (error) {
    console.error("AI receipt check failed:", error);
    if (requestId === latestAiRequestId) {
      showAiUnavailableState();
    }
  }
}
```

---

## 12. FastAPI AI Prediction Endpoint
The backend hosts a highly robust API. Inside `backend/main.py`, the endpoint is mapped to `/api/receipt/predict`:
- **FastAPI Endpoint:** `@app.post("/api/receipt/predict")`
- **Logic:** Reads the file bytes, invokes `predict_receipt` inside `backend/app/predictor.py`, and returns a detailed JSON response.

### Example API JSON Response:
```json
{
  "success": true,
  "filename": "screenshot_paytm.png",
  "prediction": "receipt",
  "status": "likely_receipt",
  "allow_submission": true,
  "receipt_probability": 96.85,
  "not_receipt_probability": 3.15,
  "quality": {
    "acceptable": true,
    "blur_detected": false,
    "brightness_issue": false
  },
  "ocr_signals": {
    "has_amount": true,
    "has_success_keyword": true,
    "has_transaction_reference": true,
    "has_failure_or_pending_keyword": false,
    "signals_found": ["paid", "₹", "utr", "gpay"],
    "ocr_signal_score": 0.8
  },
  "threshold": 92.0,
  "message": "This appears to be a successful payment receipt. Transaction verification is still required."
}
```

---

## 13. Image File Validation and Security
Before any machine learning inference begins, the image passes through the **Image Quality Gate** inside `backend/app/image_validator.py` to prevent security exploits:
1. **File Size Check:** Rejects empty files and caps images at `MAX_FILE_SIZE_BYTES` (**3 MB**) to prevent denial-of-service (DoS) exploits.
2. **Safe Decode Verification:** Passes the image bytes through `Image.open().verify()` to detect and block malformed or corrupted files.
3. **MIME Whitelisting:** Enforces a strict set of accepted MIME types (`image/jpeg`, `image/png`, `image/webp`).
4. **Grayscale Quality Analysis:** Converts the Pillow image to a grayscale NumPy array to calculate image metrics.
5. **Pure NumPy Laplacian Variance (Blur Detection):**
   - Applies a manual 3x3 Laplacian kernel over the array.
   - Variance of the output is calculated. If the variance is less than `BLUR_THRESHOLD` (**30.0**), the image is flagged as blurry.
6. **Pure NumPy Brightness Analysis:**
   - Computes the average pixel brightness value of the array.
   - If mean brightness is under **12.0**, it is flagged as extremely dark. If it exceeds **253.0**, it is flagged as overexposed.

### The Brightness Issue & Fix

> [!WARNING]
> **Project Reality Check:**  
> In an earlier design, a perfectly clear, white-background payment receipt was blocked with the message: *"Image is extremely overexposed"*.  
> **Why it happened:** Payment receipts are naturally very white and bright, pushing their average brightness values past standard image thresholds.  
> **How we fixed it:** Inside `backend/app/image_validator.py`, we raised the overexposure ceiling (`BRIGHTNESS_HIGH`) to **253.0**. More importantly, **we changed the rejection logic**: the code now **only blocks the image if BOTH blur and brightness are bad**. If only brightness is high, the quality check remains acceptable, allowing the ML model to make the final visual prediction.

---

## 14. Image Preprocessing Pipeline
To match the inputs expected by the pretrained neural network, the image is prepared inside `predictor.py` as follows:
- **Color Space:** PIL converts the image to the **RGB** color space.
- **Dimensions:** Resized to exactly **224 × 224 pixels** using a bilinear interpolation algorithm (`Image.BILINEAR`).
- **Numpy Transformation:** Converted into a float32 NumPy array with a batch dimension appended first, producing a shape of `(1, 224, 224, 3)`.
- **Normalization:** Values are scaled to the `[0.0, 1.0]` range (divided by 255.0) and preprocessed using standard EfficientNetB0 scaling parameters.

---

## 15. Training Dataset Used
The dataset used to train the classifiers is divided into separate directories inside the `dataset` folder:
- `dataset/train/`: Used to train model weights and classifier layers.
- `dataset/val/`: Used to optimize hyperparameters and prefitted calibration curves.
- `dataset/test/`: Held out strictly to measure generalized accuracy.

---

## 16. Photos Folder Usage and Labelling
To supplement the synthetic samples, original mobile screenshots were collected locally at `/Users/likithnaidu/Desktop/PHOTOS-TRAIN/photos`. 
During dataset preparation:
- Original screenshots are loaded and assigned to their respective splits.
- Real screenshots are labeled as `receipt` (1).
- Unrelated landscape, selfie, or poster screenshots are labeled as `not_receipt` (0).
- Adding high-quality, diverse negative images (specifically including phone interface screenshots, WhatsApp chats, and bank notifications) is mandatory to prevent the model from misclassifying any random mobile interface as a receipt.

---

## 17. Positive and Negative Classes
- **Positive Class (`receipt`):** Payment screenshots showing payment details, success animations, UPI transaction reference numbers, or transaction summaries from apps like Paytm, PhonePe, and Google Pay.
- **Negative Class (`not_receipt`):** Blank screens, gradients, selfies, landscapes, social media feed layouts, document files, game screens, or failed payment notification dialogs.

---

## 18. Data Augmentation Explained Deeply

> [!NOTE]
> **Telugu Meaning:**  
> "Data Augmentation అంటే... మన దగ్గర ఉన్న ఫోటోల సంఖ్య తక్కువగా ఉన్నప్పుడు, వాటిని కాస్త వంచడం (rotate), వెలుతురు మార్చడం (brightness), బ్లర్ చేయడం ద్వారా కృత్రిమంగా కొత్త ఫోటోలు సృష్టించి మోడల్ కి ఎక్కువ విషయాలు నేర్పించడం."

Data Augmentation is crucial when working with limited unique samples. If the model only trains on a few images, it will memorize the specific layouts and fail on new formats (overfitting). Inside `backend/training/grand_retrain.py`, we apply **12 augmented copies per receipt image**:
- **Rotation:** Random rotation between -15° and +15°.
- **Cropping:** Random zooming/cropping between 5% and 15%.
- **Brightness & Contrast:** Randomly scaling brightness (0.5 to 1.5) and contrast (0.6 to 1.4).
- **Blur & Noise:** Applying Gaussian blur and normal distribution noise.
- **Compression Artifacts:** Simulating low-quality JPEG saves (quality range 15 to 55).
- **Perspective Affine Shifts:** Slightly distorting the perspective layout.

---

## 19. Transfer Learning Explained
Instead of training a giant, deep neural network from scratch (which would require millions of receipt images and days of compute), we utilize **Transfer Learning**:
1. We take **EfficientNetB0**, which has already been trained on the massive **ImageNet** dataset (1.2 million images).
2. The network has already learned to detect basic visual features: edges, curves, gradients, and textures in its lower layers.
3. We freeze those lower layers and stack a custom **classification head** on top, training only our head to associate those visual shapes with event payment receipts.

---

## 20. EfficientNetB0 Explained from Beginner Level
EfficientNetB0 is a highly optimized Convolutional Neural Network (CNN) architecture. It uses a compound scaling method that balances depth, width, and resolution.
- **Input Image:** A raw 3D array of size `(224, 224, 3)`.
- **Lower Convolutional Layers:** Extract simple edges, lines, and color boundaries.
- **Middle Convolutional Layers:** Combine edges into shapes, cards, text block areas, and UI components.
- **Upper Global Average Pooling (GAP):** Condenses the final activation maps into a single flat vector of **1280 floating-point numbers**. This 1280-dimensional array represents the "visual embedding" of the screenshot.

```
Input Image (224x224x3)
         │
         ▼
[ Convolution Layers ] ──> Extracts edges, shapes, layouts
         │
         ▼
[ Global Avg Pooling ] ──> Flat numerical vector: 1280 Visual Features
         │
         ▼
[ Dense Head Layer ] ──> Maps features to final classification score
```

---

## 21. Phase 1: Head-Only Training
- **Action:** Freeze the entire pre-trained EfficientNetB0 backbone.
- **Execution:** Train only the newly added top Dense layers (128 units + Dropout + Sigmoid Output) using a standard learning rate (`1e-3`).
- **Goal:** Safely train the top head weights without distorting the highly optimized feature extraction capabilities of the lower backbone.

---

## 22. Phase 2: Fine-Tuning
- **Action:** Unfreeze the top **50 layers** of the EfficientNetB0 backbone.
- **Execution:** Train both the unfrozen base layers and the top head at a much lower learning rate (`5e-6`).
- **Goal:** Allow the highest-level convolutional filters to slightly adjust their weights, learning to recognize text card arrangements and receipt-specific layout visuals.

---

## 23. Phase 3: Full-Tuning and Early Stopping
- **Action:** Unfreeze the entire network (all backbone layers).
- **Execution:** Train at an ultra-low learning rate (`1e-6`) to prevent ruining the weights.
- **Early Stopping Callback:** Configured to monitor the validation loss. If the validation loss fails to improve for 5 consecutive epochs (`patience=5`), training terminates immediately to prevent overfitting, restoring the best model weights found during training.

---

## 24. Feature Extraction Pipeline
Once the backbone has been optimized, we detach the final classification head and treat the network solely as an **extracting tool**. 
During feature extraction, an image is passed through the ONNX feature extractor, producing a flat 1280-dimensional vector. Then, 5 quality metrics calculated using OpenCV/NumPy are appended, forming a final 1285-dimensional fused feature vector.

---

## 25. Meaning of 1280 Visual Features
The 1280 visual features represent the **Global Average Pooling** output from EfficientNetB0. They do not correspond to human-readable concepts like "transaction amount" or "logo". Instead, they represent a highly compressed numerical mapping of the layout, textures, text density, and visual patterns of the image.

---

## 26. Meaning of 5 Quality Features
To give the downstream classifier direct knowledge about the quality of the image:
1. `blur_score`: Laplacian variance value.
2. `brightness`: Grayscale pixel mean value.
3. `aspect_ratio`: Image width divided by height.
4. `width`: Original width in pixels.
5. `height`: Original height in pixels.

---

## 27. Meaning of 1285 Fused Features
The final feature vector represents the fusion of deep visual representations and direct physical attributes:
$$\text{Fused Feature Vector} = [f_{\text{visual}, 1}, f_{\text{visual}, 2}, \dots, f_{\text{visual}, 1280}, \text{blur\_score}, \text{brightness}, \text{aspect\_ratio}, \text{width}, \text{height}]$$
By combining these, the downstream classifier can easily distinguish between high-quality payment receipts, low-resolution synthetic crops, and blurry real-world photos.

---

## 28. Machine Learning Classifier Ensemble
Rather than relying on a single neural network output, the `grand_retrain` pipeline extracts features and compares 5 different machine learning classifiers:
1. **Support Vector Machine (SVM RBF):** Projects features into higher-dimensional space using radial basis functions, maximizing the separating boundary.
2. **Logistic Regression:** Simple, linear model with L2 regularization.
3. **ExtraTrees Classifier:** Extremely randomized decision tree forest.
4. **Gradient Boosting Classifier:** Sequential boosting of shallow trees.
5. **Voting Classifier Ensemble:** A soft-voting ensemble combining the outputs of all the individual classifiers.

---

## 29. Logistic Regression, SVM, ExtraTrees and GradientBoosting Comparison
During training, validation results for each classifier are collected:

| Model Name | Validation Accuracy | Validation Recall | Val False Positive Rate (FPR) | Validation ROC AUC |
| :--- | :--- | :--- | :--- | :--- |
| **SVM_RBF** | 1.0 (100%) | 1.0 (100%) | 0.0 (0%) | 1.0 (100%) |
| **ExtraTrees** | 1.0 (100%) | 1.0 (100%) | 0.0 (0%) | 1.0 (100%) |
| **GradientBoosting**| 1.0 (100%) | 1.0 (100%) | 0.0 (0%) | 1.0 (100%) |
| **LogisticRegression**| 1.0 (100%) | 1.0 (100%) | 0.0 (0%) | 1.0 (100%) |
| **Ensemble_Voting** | 1.0 (100%) | 1.0 (100%) | 0.0 (0%) | 1.0 (100%) |

---

## 30. Why the Final Classifier Was Selected
While all classifiers recorded perfect validation metrics due to the clean separation in the extracted feature space, **SVM_RBF** was selected as the final classifier. 
- **Robust Decision Boundary:** SVM RBF maximizes the margin between classes rather than just fitting a linear divider, making it more resilient to slight changes in new receipt formats.
- **Calibrated Probabilities:** Combined with isotonic calibration, SVM produces smooth, reliable probability outputs compared to the overconfident step-like curves generated by boosted tree models.

---

## 31. Calibration and Why Percentage Can Be Misleading
Raw machine learning confidence values do not represent true probabilities. An uncalibrated model might predict a receipt probability of **99%** for a completely random image simply because the image falls far on one side of a decision boundary.

```
Uncalibrated SVM Score ──> [ Isotonic Regression Curve ] ──> Calibrated Similarity %
```

To resolve this, we apply **Isotonic Calibration** using Scikit-Learn's `CalibratedClassifierCV`. It fits a non-decreasing step function that maps the raw SVM decision outputs into realistic probabilities, ensuring that if a set of receipts receive an 80% similarity score, approximately 80% of those screenshots are genuine receipts.

---

## 32. ONNX File Explained A to Z
**Open Neural Network Exchange (ONNX)** is a serialization format that allows AI models to run across different runtimes:
- **Portability:** We train the backbone using TensorFlow/Keras on a local Mac, export the feature extraction layers into a portable `receipt_feature_extractor.onnx` file, and load it in the FastAPI production backend using the lightweight `onnxruntime` library.
- **Resource Savings:** ONNX Runtime avoids the need to load the heavy TensorFlow library (saving **200+ MB of server RAM** in production).

---

## 33. PKL Files Explained A to Z
`.pkl` (Pickle) files are serialized Python objects saved using Scikit-Learn/Joblib:
- **Trained States:** They freeze the trained states of the Support Vector Machine (`receipt_classifier.pkl`) and the normalization parameters of the scaler (`feature_scaler.pkl`).
- **Input Constraints:** The classifier PKL expects a scaled 1D input array of exactly **1285 features**. Any mismatch in feature size or order will trigger a runtime error.

> [!CAUTION]
> **Security Warning:**  
> Only load pickle files created by your own training scripts. Loading arbitrary user-uploaded pickle files is highly dangerous, as Python's pickle module can execute arbitrary shell commands during deserialization.

---

## 34. Feature Scaler Explained A to Z
The `feature_scaler.pkl` contains a fitted `StandardScaler` object:
- **Feature Normalization:** Standardizes each feature by subtracting the training mean and dividing by the standard deviation.
- **Why it is needed:** Visual features have small decimal ranges (e.g., -0.5 to +0.5), while image width/height range in the thousands. Without scaling, the SVM model would completely ignore the visual embeddings and base its decision solely on the image size.

---

## 35. Model Config and Metrics JSON Explained
The configuration and metrics of the trained models are recorded in two key files inside `backend/models/`:
- **`model_config.json`:** Records the active classifier name (`SVM_RBF`), calibration method (`isotonic`), feature dimensions, and the distribution of samples used during training.
- **`training_metrics.json`:** Stores evaluation results on the held-out test split, including F1-score, balanced accuracy, ROC AUC, and the test Brier score.

---

## 36. Full Runtime Prediction Flow
The following ASCII flowchart shows exactly how an uploaded image is processed by the backend:

```
                  [ User Uploads Screenshot ]
                               │
                               ▼
            [ Stage A: Image Quality Validation ]
             (Verifies Blur, Overexposure, Size)
                               │
                               ├──────────────────────────┐
                     (Pass)    ▼                 (Fail)   ▼
        [ Stage B: ONNX Visual Extractor ]      [ Return 400 Bad Request ]
            (Generates 1280 Embeddings)         (Shows "Invalid Image" UI)
                               │
                               ▼
            [ Stage C: Feature Fusion (1285) ]
            (Appends Blur, Brightness, Size)
                               │
                               ▼
            [ Stage D: StandardScaler Normalization ]
                               │
                               ▼
            [ Stage D: Isotonic SVM Predictor ]
             (Produces Calibrated Probability)
                               │
                               ▼
            [ Stage E: Tesseract OCR Scans Text ]
             (Validates Success / Failure Cues)
                               │
                               ▼
            [ Stage F: Joint Fusion Decision Logic ]
```

---

## 37. How One Uploaded Image Becomes a Percentage
Let's trace two concrete examples to see the decision logic in action:

### Example 1: User uploads a valid Paytm payment screenshot
1. **Stage A:** The image is clear and well-lit. Laplacian variance is **85.0** (above the 30.0 blur threshold), and brightness is **180.0** (within acceptable limits). Passed.
2. **Stage B:** ONNX extracts 1280 visual layout features.
3. **Stage C & D:** Appends quality metrics, standardizes features, and SVM calculates a **98.2% calibrated probability**.
4. **Stage E:** Tesseract OCR detects: *"paid successful"*, *"₹700"*, and a UPI reference number, calculating an OCR signal score of **0.80**.
5. **Stage F:** Since `receipt_prob` (98.2%) > `THRESHOLD_LIKELY_RECEIPT` (92%) and `ocr_confirms` is true:
   - Sets status to `likely_receipt`, sets prediction to `receipt`, sets `allow_submission` to `true`.
   - Returns a successful confirmation to the frontend.

### Example 2: User uploads a selfie
1. **Stage A:** Image is clear and well-lit. Passed.
2. **Stage B:** ONNX extracts 1280 visual layout features.
3. **Stage C & D:** Appends quality metrics, standardizes features, and SVM calculates a **3.4% calibrated probability** (since the feature vector lies far from the receipt cluster).
4. **Stage E:** OCR detects no receipt keywords, producing an OCR score of **0.00**.
5. **Stage F:** The probability (3.4%) falls far below `THRESHOLD_UNCERTAIN_LOW` (70.0%):
   - Sets status to `not_receipt`, sets prediction to `not_receipt`, sets `allow_submission` to `false`.
   - The backend rejects the request, and the frontend blocks submission, showing a toast error.

---

## 38. Backend Integration with FastAPI
The FastAPI route is defined inside `backend/main.py` at `/api/receipt/predict`. The function reads the uploaded file stream:
1. It asynchronously reads the upload stream using `contents = await file.read()`.
2. Invokes `predict_receipt(contents, ...)` in `app.predictor`.
3. Handles exceptions gracefully by logging failures to the database using `log_problem_to_db` and returning safe fallback dictionaries.

---

## 39. Frontend Display of AI Similarity Score
The frontend processes the returned API JSON response:
1. If the API returns successfully, it updates the global variable `aiAllowSubmission` with the backend's `allow_submission` flag.
2. It animates the circular ring progress using `conic-gradient` step-by-step from 0% to the target probability.
3. Updates the badge text (`Verified`, `Review Needed`, or `Rejected`) and colors the panel border based on the returned state.

---

## 40. Database Storage of AI Result, If Implemented
During a successful registration submit (`/api/register`), the AI validation result is committed directly to the database:
- **Active Columns:**
  - `ai_receipt_match_score`: Stores the similarity percentage.
  - `ai_receipt_label`: Stores the prediction label (`payment_receipt`, `needs_review`, `non_receipt`).
  - `ai_receipt_model_version`: Active system version (`multi-stage-v1`).
  - `ai_receipt_checked_at`: Timestamp of the AI check.
- **Backend Lock:** If the final prediction returns `not_receipt` or `suspicious_or_not_successful`, the database insert is blocked, and the server returns a `400 Bad Request` directly.

---

## 41. Admin Manual Verification Flow
The CRM admin dashboard displays all submitted registrations. Because the AI is only a visual filter, the organizer must perform manual verification:
1. The admin reviews the UTR ID and compares the uploaded screenshot preview side-by-side.
2. The admin logs into their bank portal to verify that a transaction matching the UTR ID and amount has indeed arrived.
3. Once verified, the admin clicks **Approve**, triggering a confirmation email to the attendee in the background.

---

## 42. Real-World Testing and Metrics
Real-world testing was conducted on a validation pool of **29 user payment screenshots**:
- **Result:** **27** screenshots were correctly identified as receipts, while **2** were classified as not receipts.
- **Recall Rate:** This indicates a real-world recall rate of **93.1%** ($\frac{27}{29}$).
- **Missing Test Scenarios:** While recall on real receipts is high, the model must still be aggressively tested against adversarial negatives, including failed transaction screens, cropped logos, and mobile screenshot interfaces.

---

## 43. Why 100% Accuracy Must Be Treated Carefully

> [!WARNING]
> **Project Reality Check:**  
> The training logs claim a validation accuracy of **100%** (`val_acc: 1.0`). In real-world machine learning, **100% accuracy is a red flag indicating overfitting or data leakage!**  
> **The source of the leakage:** In our training pipeline, the EfficientNetB0 backbone was fine-tuned on the validation directory. Since the backbone has already "seen" the validation images, the extracted validation features are extremely clustered, leading to inflated, perfect metrics. True production performance will vary and must be measured on completely unseen, external datasets.

---

## 44. Previous Human Photo 94% Failure Analysis
In an older iteration, an uploaded human photo received a **94% receipt similarity score**:
- **Root Cause:** The training dataset's negative class was too small and lacked variety, containing only blank solid colors and basic gradients. The model learned that *"any complex image with fine lines and colors is a receipt"*. When a human photo was uploaded, its complex visual textures matched the model's receipt cluster, triggering a high confidence score.

---

## 45. How the Retraining Tried to Fix That Problem
To fix this, the new `grand_retrain.py` pipeline:
1. **Added Synthetic Selfies:** Embedded `_gen_selfie()` to generate fake skin-colored ellipses and hair-like circles.
2. **Added Document Mockups:** Embedded `_gen_document()` to generate lines of text and empty form fields.
3. **Appended Quality Features:** Combined physical image features (width, height, blur) to help the model distinguish real phone screenshots from camera photos.

---

## 46. Strict Independent Testing Required
To guarantee production stability, developers must verify the model against completely independent data:
- **Test self-captured receipts:** Verify the model on new UPI screenshots from apps not included in the original training set.
- **Test adversarial selfies:** Upload photos of faces, random documents, and scenery to ensure the model outputs a low probability score.
- **Verify OCR failure logic:** Upload a screenshot showing a **"Payment Failed"** or **"Transaction Cancelled"** screen to ensure the OCR pipeline flags it as a failure.

---

## 47. Performance and Render Deployment
Deploying deep learning models to production requires careful resource management:
- **Memory Footprint:** Running the model via ONNX Runtime avoids loading heavy frameworks like TensorFlow, allowing the backend to run easily on Render's free tier (**512MB RAM limit**).
- **Startup Latency:** Inside `main.py`, the models are loaded in a **background thread** at startup:
  ```python
  @app.on_event("startup")
  def startup_event():
      from app.predictor import load_models_background
      load_models_background()
  ```
  This allows the server to bind to its port immediately, preventing Render from killing the deployment due to slow startup times.

---

## 48. Security and Privacy of Receipt Images
Payment screenshots contain highly sensitive data: UTR IDs, sender names, and transaction details.
- **Commit Safety:** Never commit the `.env` file, the sqlite database (`fallback_event_db.db`), or raw user images to public GitHub repositories.
- **Secure Key Storage:** Sensitive variables like `RESEND_API_KEY` must be configured inside Render's environment variables.
- **Secure Pickle Loading:** Never run the backend using untrusted pickle files.

---

## 50. How to Add More Training Photos Correctly
To continuously improve the accuracy of the system:
1. **Place Raw Screenshots:** Copy new payment screenshots and negative images into `/Users/likithnaidu/Desktop/forms-project/dataset/raw/`.
2. **Label Images:** Sort them into the correct directories:
   - Positive samples: `dataset/raw/receipt/`
   - Negative samples: `dataset/raw/not_receipt/`
3. **Avoid Duplicates:** Ensure that identical or highly similar images are not added multiple times, as this will lead to overfitting.

---

## 51. How to Retrain the Model Again
Execute the retraining pipeline using the terminal:
```bash
python /Users/likithnaidu/Desktop/forms-project/backend/training/grand_retrain.py
```
This script will automatically:
- Rebalance training splits.
- Generate synthetic negatives (memes, selfies, landscapes).
- Fine-tune the EfficientNetB0 backbone.
- Search for the best Scikit-Learn classifier.
- Apply isotonic calibration and output new model checkpoints.

---

## 52. How to Export and Deploy the New Model
1. The `grand_retrain.py` script automatically exports the updated models directly to `backend/models/`.
2. Commit the new `.onnx` and `.pkl` files to your private git repository or deploy them directly to your Render server.
3. Restart the FastAPI backend server to load the new checkpoints.

---

## 53. Future Accuracy Improvements
To push the system towards higher production reliability:
1. **Collect Diverse Receipts:** Add genuine screenshots from regional banks and lesser-known UPI apps.
2. **Enhance OCR Verification:** Expand the list of verified UPI keywords inside `backend/app/settings.py` to match new payment apps.
3. **Explore YOLO Object Detection:** Train a YOLO model to locate and crop the specific transaction card inside the screenshot before performing visual classification.

---

## 54. Viva / Interview Questions and Answers

### Q1: Why did you use EfficientNetB0 instead of a standard ResNet?
**Interview Answer:** EfficientNetB0 uses a compound scaling method that balances depth, width, and resolution. This makes it highly lightweight (around 16MB in ONNX format) and fast, allowing it to run within low memory limits like Render's free tier while maintaining high feature extraction accuracy.

### Q2: What is the purpose of the `.pkl` files in your pipeline?
**Interview Answer:** The `.pkl` files store the serialized states of our Scikit-Learn models. `feature_scaler.pkl` standardizes the extracted features, and `receipt_classifier.pkl` loads our trained SVM classifier and isotonic calibration curves to make the final prediction.

### Q3: Why is a manual verification step still required?
**Interview Answer:** The AI model only evaluates the visual layout of the screenshot and scans for keywords. It cannot verify whether the transaction has actually completed or if the money has successfully arrived in our bank account. Manual statement verification is mandatory to prevent fraudulent submissions.

---

## 55. One-Minute Product Explanation
> "Our SAKRA VISION Event Registration Platform features a multi-stage AI receipt validation pipeline. When an attendee uploads their transaction screenshot, the system instantly runs visual and OCR checks to verify that it is a valid payment receipt. This blocks fake submissions immediately, while organizers can review pre-validated submissions directly from their administrative dashboard, saving hours of manual review."

---

## 56. Glossary
- **CNN (Convolutional Neural Network):** A deep learning architecture designed for image processing.
- **ONNX (Open Neural Network Exchange):** A cross-platform format used to run models across different frameworks.
- **Transfer Learning:** Repurposing a pre-trained model on a new, specific task.
- **Isotonic Calibration:** A method used to map raw classifier scores into realistic probability percentages.
- **UTR (Unique Transaction Reference):** The unique 12-digit number used to track UPI transactions.

---

## 57. Final Summary
The SAKRA VISION AI Receipt Validation system combines deep visual feature extraction (ONNX EfficientNetB0), physical quality metrics fusion, calibrated SVM classification, and PyTesseract OCR. This multi-stage check provides a premium, highly secured event registration platform, blocking spam uploads and streamlining the manual verification process for organizers.
