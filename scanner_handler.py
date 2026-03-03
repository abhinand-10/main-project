import cv2
import numpy as np
import os
from PyQt5.QtWidgets import QFileDialog

class BiometricHandler:
    def __init__(self):
        # Mantra ആപ്പ് ഫയലുകൾ സേവ് ചെയ്യുന്ന ലൊക്കേഷൻ
        self.target_folder = r"C:\Program Files\Mantra\MFS100\Driver\MFS100Test\FingerData"
        
        # ഫോൾഡർ ഇല്ലെങ്കിൽ അത് ക്രിയേറ്റ് ചെയ്യും (എറർ ഒഴിവാക്കാൻ)
        if not os.path.exists(self.target_folder):
            os.makedirs(self.target_folder, exist_ok=True)
            
        print(f"Manual Mode Active. Path: {self.target_folder}")

    def capture_fingerprint(self):
        """
        Mantra ഫോൾഡറിൽ നിന്ന് ഒരു വിരലടയാള ചിത്രം തിരഞ്ഞെടുക്കാൻ സഹായിക്കുന്നു.
        തിരഞ്ഞെടുത്ത ഫയലിന്റെ Binary Data ഇത് റിട്ടേൺ ചെയ്യും.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Fingerprint Image", self.target_folder,
            "Images (*.bmp *.jpg *.png *.jpeg);;All Files (*)", options=options
        )
        
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading file: {e}")
                return None
        return None

    def verify_match(self, stored_img_bytes, live_img_bytes):
        """
        ORB Algorithm ഉപയോഗിച്ച് രണ്ട് വിരലടയാളങ്ങൾ തമ്മിൽ താരതമ്യം ചെയ്യുന്നു.
        ഒരേ ഫയൽ ആയിരിക്കണം എന്ന് നിർബന്ധമില്ല, ഒരേ വിരലിന്റെ വ്യത്യസ്ത ചിത്രങ്ങൾ ആയാലും ഇത് തിരിച്ചറിയും.
        """
        try:
            # Binary data-യെ OpenCV ഇമേജ് ഫോർമാറ്റിലേക്ക് മാറ്റുന്നു
            nparr1 = np.frombuffer(stored_img_bytes, np.uint8)
            img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)

            nparr2 = np.frombuffer(live_img_bytes, np.uint8)
            img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)

            if img1 is None or img2 is None:
                print("Error: Could not decode images.")
                return False

            # ORB Detector ക്രിയേറ്റ് ചെയ്യുന്നു (വിരലടയാളത്തിലെ പ്രത്യേക പോയിന്റുകൾ കണ്ടെത്താൻ)
            orb = cv2.ORB_create(nfeatures=1000)

            # കീപോയിന്റുകൾ കണ്ടെത്തുന്നു (Keypoints and Descriptors)
            kp1, des1 = orb.detectAndCompute(img1, None)
            kp2, des2 = orb.detectAndCompute(img2, None)

            if des1 is None or des2 is None:
                return False

            # ബ്രൂട്ട് ഫോഴ്സ് മാച്ചർ ഉപയോഗിച്ച് പോയിന്റുകൾ ഒത്തുനോക്കുന്നു
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)

            # സമാനമായ പോയിന്റുകളുടെ എണ്ണം (Score)
            score = len(matches)
            print(f"--- Fingerprint Match Score: {score} ---")

            # മാച്ചിംഗ് ലിമിറ്റ് (Threshold)
            # 40-നും 60-നും ഇടയിലുള്ള വാല്യൂ ആണ് നല്ലത്. 
            # സ്കാനർ ക്വാളിറ്റി കുറവാണെങ്കിൽ 35-ലേക്ക് കുറയ്ക്കാം.
            if score > 45: 
                print("Result: MATCH SUCCESS ✅")
                return True
            else:
                print("Result: MATCH FAILED ❌")
                return False

        except Exception as e:
            print(f"Verification Logic Error: {e}")
            return False

    def close(self):
        """സിസ്റ്റം ക്ലോസ് ചെയ്യുമ്പോൾ ആവശ്യമായവ ഇവിടെ നൽകാം"""
        pass