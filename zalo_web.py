from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

class ZaloBot:
    def __init__(self):
        # Cấu hình cho Cốc Cốc
        coc_coc_options = webdriver.ChromeOptions()
        coc_coc_options.binary_location = "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe"  # Thay đổi đường dẫn phù hợp
        
        # Thêm các tùy chọn nếu cần
        # coc_coc_options.add_argument('--start-maximized')
        # coc_coc_options.add_argument('--disable-notifications')
        
        self.driver = webdriver.Chrome(options=coc_coc_options)
        self.wait = WebDriverWait(self.driver, 10)
        # Thêm biến để lưu lịch sử chat
        self.chat_history = []
        self.ai_enabled = False  # Thêm biến để theo dõi trạng thái AI
    
    def login_zalo(self):
        self.driver.get("https://chat.zalo.me")
        # Đợi người dùng đăng nhập thủ công bằng QR code
        input("Vui lòng quét mã QR để đăng nhập và nhấn Enter để tiếp tục...")
    
    def get_latest_message(self):
        try:
            # Đợi và lấy tất cả tin nhắn (bao gồm cả tin nhắn của mình)
            message_elements = self.wait.until(
                EC.presence_of_all_elements_located((
                    By.CSS_SELECTOR, 
                    "div.chat-item span.text"  # Bỏ :not(.me) để lấy cả tin nhắn của mình
                ))
            )
            if message_elements:
                latest_message = message_elements[-1].text
                print(f"Tin nhắn mới nhất: {latest_message}")
                return latest_message
            return None
        except Exception as e:
            print(f"Lỗi khi đọc tin nhắn: {e}")
            return None

    def clean_message(self, message):
        try:
            # Loại bỏ emoji và ký tự đặc biệt
            import re
            # Giữ lại chữ, số, dấu câu cơ bản
            cleaned = re.sub(r'[^\w\s.,!?()-]', '', message)
            return cleaned.strip()
        except Exception as e:
            print(f"Lỗi khi xử lý tin nhắn: {e}")
            return message

    def send_message(self, message):
        try:
            # Làm sạch tin nhắn trước khi gửi
            clean_msg = self.clean_message(message)
            
            # Tìm ô nhập tin nhắn và gửi
            input_box = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#richInput"
                ))
            )
            input_box.send_keys(clean_msg)
            
            # Tìm nút gửi
            send_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                "div[data-translate-title='STR_SEND']"
            )
            send_button.click()
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn: {e}")

    def process_messages(self):
        print("Bắt đầu theo dõi tin nhắn...")
        last_processed_message = None
        consecutive_errors = 0  # Đếm số lần lỗi liên tiếp
    
        while True:
            try:
                latest_message = self.get_latest_message()
                
                if latest_message and latest_message != last_processed_message:
                    print(f"Tin nhắn mới nhận được: {latest_message}")
                    
                    # Kiểm tra các lệnh @ai
                    if latest_message.lower().startswith("@ai"):
                        command = latest_message[4:].strip().lower()  # Lấy phần sau @ai
                        
                        if command == "on":
                            self.ai_enabled = True
                            self.send_message("AI đã được bật")
                            consecutive_errors = 0
                            last_processed_message = latest_message
                            continue
                        elif command == "off":
                            self.ai_enabled = False
                            self.send_message("AI đã được tắt")
                            consecutive_errors = 0
                            last_processed_message = latest_message
                            continue
                        elif command:  # Nếu có nội dung sau @ai
                            print("Xử lý lệnh trực tiếp với AI...")
                            try:
                                with ThreadPoolExecutor() as executor:
                                    future = executor.submit(self.get_ai_response, command)
                                    try:
                                        ai_response = future.result(timeout=30)
                                        if ai_response:
                                            print(f"Phản hồi từ AI: {ai_response}")
                                            self.send_message(ai_response)
                                            print("Đã gửi phản hồi")
                                            consecutive_errors = 0
                                        else:
                                            raise Exception("Không nhận được phản hồi từ AI")
                                    except TimeoutError:
                                        raise Exception("AI phản hồi quá thời gian")
                            except Exception as ai_error:
                                print(f"Lỗi AI: {ai_error}")
                                consecutive_errors += 1
                                if consecutive_errors >= 3:
                                    self.ai_enabled = False
                                    self.send_message("AI đã tự động tắt do gặp lỗi liên tục. Vui lòng kiểm tra kết nối và bật lại bằng lệnh @ai on")
                                    consecutive_errors = 0
                            last_processed_message = latest_message
                            continue
                    
                    # Xử lý tin nhắn thông thường khi AI được bật
                    is_own_message = self.driver.find_elements(By.CSS_SELECTOR, "div.chat-item.me span.text")[-1].text == latest_message
                    if not is_own_message and self.ai_enabled:
                        print("Đang xử lý với AI...")
                        try:
                            # Thêm timeout cho việc lấy phản hồi AI
                            with ThreadPoolExecutor() as executor:
                                future = executor.submit(self.get_ai_response, latest_message)
                                try:
                                    ai_response = future.result(timeout=30)  # Timeout sau 30 giây
                                    if ai_response:
                                        print(f"Phản hồi từ AI: {ai_response}")
                                        self.send_message(ai_response)
                                        print("Đã gửi phản hồi")
                                        consecutive_errors = 0  # Reset số lần lỗi nếu thành công
                                    else:
                                        raise Exception("Không nhận được phản hồi từ AI")
                                except TimeoutError:
                                    raise Exception("AI phản hồi quá thời gian")
                        except Exception as ai_error:
                            print(f"Lỗi AI: {ai_error}")
                            consecutive_errors += 1
                            if consecutive_errors >= 3:  # Nếu lỗi 3 lần liên tiếp
                                self.ai_enabled = False
                                self.send_message("AI đã tự động tắt do gặp lỗi liên tục. Vui lòng kiểm tra kết nối và bật lại bằng lệnh @ai on")
                                consecutive_errors = 0
                    
                    last_processed_message = latest_message
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Có lỗi xảy ra: {e}")
                consecutive_errors += 1
                if consecutive_errors >= 3:  # Nếu lỗi 3 lần liên tiếp
                    self.ai_enabled = False
                    try:
                        self.send_message("AI đã tự động tắt do gặp lỗi liên tục. Vui lòng kiểm tra kết nối và bật lại bằng lệnh @ai on")
                    except:
                        print("Không thể gửi thông báo lỗi")
                    consecutive_errors = 0
                time.sleep(1)
    
    def get_ai_response(self, message):
        try:
            import os
            import google.generativeai as genai

            # Cấu hình API key cho Gemini từ biến môi trường
            genai.configure(api_key="AIzaSyB_eNpMTroPTupXzl_oey08M0d-luxJ3OE")

            # Cấu hình tham số cho model
            generation_config = {
                "temperature": 1,
                "top_p": 0.95, 
                "top_k": 64,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }

            # Khởi tạo model với cấu hình
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
            )

            # Chuyển đổi lịch sử chat sang format phù hợp với Gemini
            formatted_history = []
            for msg in self.chat_history:
                if msg["role"] == "user":
                    formatted_history.append({"parts": [{"text": msg["content"]}], "role": "user"})
                else:
                    formatted_history.append({"parts": [{"text": msg["content"]}], "role": "model"})

            # Tạo phiên chat với lịch sử đã format
            chat_session = model.start_chat(history=formatted_history)

            # Thêm tin nhắn mới vào lịch sử với format mới
            self.chat_history.append({"role": "user", "content": message})

            # Tạo prompt theo yêu cầu
            prompt = f"""
            Bạn là trợ lý AI trả lời tin nhắn Zalo. Hãy tuân thủ nghiêm ngặt:
             1. LUÔN trả lời trực tiếp, không được hỏi lại người dùng
            2. Sử dụng tiếng Việt có dấu, không dùng markdown hay ký tự đặc biệt
            3. KHÔNG ĐƯỢC dùng các cụm từ như "Xin lỗi", "Tôi không hiểu"
            4. PHẢI trả lời dứt khoát và hữu ích
            5. KHÔNG ĐƯỢC dùng emoji hoặc ký tự đặc biệt
            6. Trả lời như cuộc trò chuyện thông thường
            
            Tin nhắn cần phản hồi: {message}
        
            Hãy phân tích và trả lời ngay như một cuộc trò chuyện bình thường:
            """

            # Gửi prompt và nhận phản hồi
            response = chat_session.send_message(prompt)
            
            # Lưu phản hồi vào lịch sử
            self.chat_history.append({"role": "assistant", "content": response.text})
            
            return response.text
        except Exception as e:
            print(f"Lỗi khi lấy phản hồi từ Gemini: {e}")
            return None

def main():
    bot = ZaloBot()
    bot.login_zalo()
    bot.process_messages()

if __name__ == "__main__":
    main()
