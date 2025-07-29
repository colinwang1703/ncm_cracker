from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import binascii
import struct
import base64
import json
import os
import threading
import time
from Crypto.Cipher import AES

# 全局锁用于文件写入
file_lock = threading.Lock()

def decrypt_chunk(chunk, key_box, start_offset):
    """优化的块解密函数"""
    chunk_length = len(chunk)
    decrypted = bytearray(chunk_length)
    
    for i in range(chunk_length):
        j = (start_offset + i + 1) & 0xff
        decrypted[i] = chunk[i] ^ key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
    
    return decrypted

def dump(file_path, name):
    """优化的解密函数"""
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s: s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    
    try:
        with open(file_path, 'rb') as f:
            # 验证文件头
            header = f.read(8)
            assert binascii.b2a_hex(header) == b'4354454e4644414d'
            f.seek(2, 1)
            
            # 读取并解密密钥
            key_length = struct.unpack('<I', f.read(4))[0]
            key_data = bytearray(f.read(key_length))
            for i in range(len(key_data)):
                key_data[i] ^= 0x64
            
            cryptor = AES.new(core_key, AES.MODE_ECB)
            key_data = unpad(cryptor.decrypt(key_data))[17:]
            
            # 生成密钥盒
            key_box = bytearray(range(256))
            c = 0
            last_byte = 0
            key_offset = 0
            key_length = len(key_data)
            
            for i in range(256):
                swap = key_box[i]
                c = (swap + last_byte + key_data[key_offset]) & 0xff
                key_offset = (key_offset + 1) % key_length
                key_box[i] = key_box[c]
                key_box[c] = swap
                last_byte = c
            
            # 读取元数据
            meta_length = struct.unpack('<I', f.read(4))[0]
            meta_data = bytearray(f.read(meta_length))
            for i in range(len(meta_data)):
                meta_data[i] ^= 0x63
            
            meta_data = base64.b64decode(meta_data[22:])
            cryptor = AES.new(meta_key, AES.MODE_ECB)
            meta_data = json.loads(unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:])
            
            # 跳过CRC32和封面数据
            f.seek(4, 1)  # CRC32
            f.seek(5, 1)  # gap
            image_size = struct.unpack('<I', f.read(4))[0]
            f.seek(image_size, 1)  # 跳过封面数据
            
            # 准备输出文件
            file_name = os.path.splitext(os.path.basename(file_path))[0] + '.' + meta_data['format']
            output_path = os.path.join(os.path.dirname(file_path), file_name)
            
            # 获取音频数据大小
            audio_start = f.tell()
            f.seek(0, 2)  # 移到文件末尾
            total_size = f.tell() - audio_start
            f.seek(audio_start)  # 回到音频数据开始位置
            
            # 使用更大的缓冲区进行解密
            BUFFER_SIZE = 0x40000  # 256KB 缓冲区
            
            with open(output_path, 'wb') as output_file:
                processed = 0
                print(f"正在解密: {name[:20].ljust(20)} -> {file_name}")
                
                while processed < total_size:
                    chunk = f.read(min(BUFFER_SIZE, total_size - processed))
                    if not chunk:
                        break
                    
                    # 解密数据块
                    decrypted_chunk = decrypt_chunk(chunk, key_box, processed)
                    output_file.write(decrypted_chunk)
                    processed += len(chunk)
                
                print(f"完成解密: {name[:20].ljust(20)} ({processed:,} bytes)")
        
        # 线程安全地写入已处理文件列表
        with file_lock:
            with open('cracked.txt', 'a', encoding='utf-8') as f:
                f.write(name + '\n')
        
        return file_name
        
    except Exception as e:
        print(f"解密失败 {name}: {str(e)}")
        return None

def process_file_wrapper(args):
    """多进程包装函数"""
    file_path, name = args
    return dump(file_path, name)

def main():
    """主函数，实现并行处理"""
    try:
        with open('cracked.txt', 'r', encoding='utf-8') as f:
            cracked = set(f.read().strip().split('\n'))
    except FileNotFoundError:
        cracked = set()
    
    # 查找需要处理的文件
    current_directory = os.getcwd()
    files_to_process = []
    
    for file in os.listdir(current_directory):
        if file.endswith('.ncm'):
            name = file[:-4]
            if name not in cracked:
                filepath = os.path.join(current_directory, file)
                files_to_process.append((filepath, name))
    
    if not files_to_process:
        print("没有找到需要处理的 .ncm 文件")
        return
    
    print(f"找到 {len(files_to_process)} 个文件需要处理")
    
    # 确定并行进程数（不超过CPU核心数，也不超过文件数）
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 4)
    print(f"使用 {max_workers} 个并行进程")
    
    # 并行处理文件
    successful = 0
    failed = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file = {
            executor.submit(process_file_wrapper, file_info): file_info[1] 
            for file_info in files_to_process
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_file):
            file_name = future_to_file[future]
            try:
                result = future.result()
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {str(e)}")
                failed += 1
    
    print(f"\n处理完成！成功: {successful}, 失败: {failed}")

if __name__ == '__main__':
    main()