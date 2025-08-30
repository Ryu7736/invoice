from flask import Blueprint,jsonify
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR
import numpy as np
import cv2
import re

def preprocess_image_light(img_array):
    """軽い前処理で認識精度を向上"""
    try:
        print("[DEBUG] 前処理開始")
        
        # 1. グレースケール変換
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        print(f"[DEBUG] グレースケール変換完了: {gray.shape}")
        
        # 2. 軽いコントラスト調整
        enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
        print("[DEBUG] 軽いコントラスト調整完了")
        
        # 3. ノイズ除去（軽い）
        denoised = cv2.medianBlur(enhanced, 3)
        print("[DEBUG] ノイズ除去完了")
        
        return denoised
        
    except Exception as e:
        print(f"[ERROR] 前処理でエラー: {e}")
        return img_array  # エラー時は元画像を返す

def ocr(files):
    results = []
    for f in files:
        try:
            print("[DEBUG] OCR処理開始")
            pdf_bytes = f.read()
            if not pdf_bytes:
                return "f.read()失敗"
            
            print(f"[DEBUG] PDF読み込み完了: {len(pdf_bytes)} bytes")
            
            imgs = convert_from_bytes(pdf_bytes, dpi=200, fmt="png")
            print(f"[DEBUG] PDF変換完了: {len(imgs)}ページ")

            for i, img in enumerate(imgs):
                print(f"[DEBUG] ページ{i+1}処理開始")
                img_array = np.array(img)
                print(f"[DEBUG] 画像配列変換完了: {img_array.shape}")
                
                # 🔧 前処理を追加
                try:
                    processed_img = preprocess_image_light(img_array)
                    print("[DEBUG] 前処理完了")
                except Exception as e:
                    print(f"[WARNING] 前処理失敗、元画像を使用: {e}")
                    processed_img = img_array
                
                # 🔧 OCRモデルのパラメータを最適化
                ocr_model = PaddleOCR(
                    lang="japan",
                    use_angle_cls=True,
                    show_log=False,
                    det_db_thresh=0.3,      # 検出感度調整
                    det_db_box_thresh=0.5,  # ボックス信頼度
                    det_limit_side_len=2000 # 高解像度対応
                )
                
                print("[DEBUG] OCR実行中...")
                ocr_result = ocr_model.ocr(processed_img)
                print(f"[DEBUG] OCR実行完了: 長さ={len(ocr_result)}")
                
                page_texts = []
                
                # 🔧 正しい構造に対応: 各要素が [[[座標]], ('テキスト', 信頼度)]
                if ocr_result and len(ocr_result) > 0:
                    print(f"[DEBUG] 標準構造で処理開始: {len(ocr_result)}個の要素")
                    
                    for j, line in enumerate(ocr_result):
                        if j < 5:  # 最初の5個だけ詳細ログ
                            print(f"[DEBUG] 要素{j}: {line}")
                        
                        # 標準的な構造: [[[座標]], ('テキスト', 信頼度)]
                        if (isinstance(line, list) and len(line) >= 2 and 
                            isinstance(line[1], tuple) and len(line[1]) >= 2):
                            
                            text = line[1][0]
                            confidence = line[1][1]
                            
                            if j < 10:  # 最初の10個だけ詳細ログ
                                print(f"[DEBUG] 抽出: '{text}' (信頼度: {confidence:.3f})")
                            
                            # 🔧 信頼度フィルタを追加
                            if (text and isinstance(text, str) and text.strip() and 
                                confidence > 0.6):  # 60%以上の信頼度
                                
                                # 後処理を適用
                                corrected_text = post_process_text(text.strip())
                                page_texts.append(corrected_text)
                                
                                if j < 10:
                                    print(f"[DEBUG] ✅ 追加: '{text}' → '{corrected_text}'")
                            else:
                                if j < 10:
                                    print(f"[DEBUG] ❌ 低信頼度またはテキスト無効: {text} (信頼度: {confidence:.3f})")
                        else:
                            if j < 10:
                                print(f"[DEBUG] ❌ 構造不正: {line}")
                
                print(f"[DEBUG] 最終結果: {len(page_texts)}個のテキスト抽出")
                results.append(page_texts)

        except Exception as e:
            print(f"[ERROR] OCR処理エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"OCR処理中にエラーが発生しました: {str(e)}"

    print(f"[DEBUG] 処理完了: 合計{sum(len(r) for r in results)}個のテキスト")
    return results

def post_process_text(text):
    """テキストの後処理で一般的な誤認識を修正"""
    
    # よくある誤認識パターンの修正
    corrections = {
        # 数字の誤認識
        'Ｏ': '0', 'ｏ': '0', 'Ｉ': '1', 'ｌ': '1', 'Ｓ': '5',
        
        # よく出現する単語の修正
        '青報': '情報',
        '卒業仏要': '卒業必要',
        'リテラシ-': 'リテラシー',
        'エンジニ': 'エンジニア',
        'アリング': 'アリング',
        'コンピ': 'コンピュ',
        'ュータ': 'ュータ',
        
        # 記号の修正
        'ć': '',
        'Å': 'A',
        'é': '',
        '」': '',
        '「': '',
        '仏': '必'
    }
    
    corrected = text
    for wrong, correct in corrections.items():
        corrected = corrected.replace(wrong, correct)
    
    # 🔧 特殊パターンの修正
    # 年度の修正 (292X年 → 202X年)
    corrected = re.sub(r'292([0-9])年', r'202\1年', corrected)
    
    # 日付の修正 (2925/98/23 → 2025/08/23)
    corrected = re.sub(r'2925/98/23', '2025/08/23', corrected)
    corrected = re.sub(r'292([0-9])/([0-9]{1,2})/([0-9]{1,2})', r'202\1/\2/\3', corrected)
    
    # よくある数字の修正
    corrected = re.sub(r'([0-9])ć', r'\1', corrected)  # 数字+ć → 数字のみ
    
    return corrected