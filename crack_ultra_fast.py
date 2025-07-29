"""
超快速 NCM 解密器
使用多种优化技术：
1. NumPy 向量化操作
2. 预计算查找表
3. 内存映射文件
4. 多进程并行
"""

import numpy as np
import mmap
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import binascii
import struct
import base64
import json
import os
import threading
from Crypto.Cipher import AES
import time

# 全局锁
file_lock = threading.Lock()

def create_key_lookup_table(key_box):
    """预计算密钥查找表以加速解密"""
    lookup_table = np.zeros(256, dtype=np.uint8)
    for j in range(256):
        lookup_table[j] = key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
    return lookup_table

def decrypt_chunk_vectorized(chunk_data, key_lookup, start_offset):
    """使用 NumPy 向量化操作进行超快速解密"""
    chunk_array = np.frombuffer(chunk_data, dtype=np.uint8)
    indices = np.arange(1, len(chunk_data) + 1, dtype=np.uint32)
    indices = (start_offset + indices) & 0xff
    
    # 向量化异或操作
    decrypted = chunk_array ^ key_lookup[indices]
    return decrypted.tobytes()

def dump_ultra_fast(file_path, name):
    """超快速解密函数"""
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s: s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    
    try:
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as f:
            # 使用内存映射加速文件读取
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                # 验证文件头
                if mmapped_file[:8] != b'CTENFDAM':
                    raise ValueError("Invalid NCM file format")
                
                offset = 10  # 跳过文件头和2字节间隔
                
                # 读取并解密密钥
                key_length = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4
                
                key_data = bytearray(mmapped_file[offset:offset+key_length])
                offset += key_length
                
                # 优化的异或操作
                key_data = np.frombuffer(key_data, dtype=np.uint8) ^ 0x64
                
                cryptor = AES.new(core_key, AES.MODE_ECB)
                key_data = unpad(cryptor.decrypt(key_data.tobytes()))[17:]
                
                # 生成密钥盒（这部分无法避免循环）
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
                
                # 预计算查找表
                key_lookup = create_key_lookup_table(key_box)
                
                # 读取元数据
                meta_length = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4
                
                meta_data = np.frombuffer(
                    mmapped_file[offset:offset+meta_length], 
                    dtype=np.uint8
                ) ^ 0x63
                offset += meta_length
                
                meta_data = base64.b64decode(meta_data.tobytes()[22:])
                cryptor = AES.new(meta_key, AES.MODE_ECB)
                meta_data = json.loads(unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:])
                
                # 跳过CRC32和封面数据
                offset += 4  # CRC32
                offset += 5  # gap
                image_size = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4 + image_size
                
                # 准备输出文件
                file_name = os.path.splitext(os.path.basename(file_path))[0] + '.' + meta_data['format']
                output_path = os.path.join(os.path.dirname(file_path), file_name)
                
                # 音频数据处理
                audio_data_size = file_size - offset
                CHUNK_SIZE = 1024 * 1024  # 1MB 块大小
                
                print(f"超快速解密: {name[:20].ljust(20)} ({audio_data_size:,} bytes)")
                start_time = time.time()
                
                with open(output_path, 'wb') as output_file:
                    processed = 0
                    
                    while processed < audio_data_size:
                        chunk_size = min(CHUNK_SIZE, audio_data_size - processed)
                        chunk_data = mmapped_file[offset + processed:offset + processed + chunk_size]
                        
                        # 使用向量化解密
                        decrypted_chunk = decrypt_chunk_vectorized(chunk_data, key_lookup, processed)
                        output_file.write(decrypted_chunk)
                        processed += chunk_size
                
                elapsed = time.time() - start_time
                speed = audio_data_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
                print(f"完成解密: {name[:20].ljust(20)} ({speed:.1f} MB/s)")
        
        # 线程安全地写入已处理文件列表
        with file_lock:
            with open('cracked.txt', 'a', encoding='utf-8') as f:
                f.write(name + '\n')
        
        return file_name
        
    except Exception as e:
        print(f"超快速解密失败 {name}: {str(e)}")
        return None

def process_file_ultra_fast(args):
    """多进程包装函数"""
    file_path, name = args
    return dump_ultra_fast(file_path, name)

def main_ultra_fast():
    """主函数，实现超快速并行处理"""
    print("=== NCM 超快速解密器 ===")
    print("使用优化技术：NumPy向量化 + 内存映射 + 多进程并行")
    
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
    
    total_size = sum(os.path.getsize(fp) for fp, _ in files_to_process)
    print(f"找到 {len(files_to_process)} 个文件需要处理 (总大小: {total_size/(1024*1024):.1f} MB)")
    
    # 确定并行进程数
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 6)
    print(f"使用 {max_workers} 个并行进程")
    
    # 并行处理文件
    successful = 0
    failed = 0
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file = {
            executor.submit(process_file_ultra_fast, file_info): file_info[1] 
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
    
    elapsed = time.time() - start_time
    total_speed = total_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
    
    print(f"\n=== 处理完成 ===")
    print(f"成功: {successful}, 失败: {failed}")
    print(f"总耗时: {elapsed:.2f} 秒")
    print(f"平均速度: {total_speed:.1f} MB/s")

if __name__ == '__main__':
    # 检查是否安装了 numpy
    try:
        import numpy as np
        main_ultra_fast()
    except ImportError:
        print("错误: 需要安装 numpy 才能使用超快速模式")
        print("请运行: pip install numpy")
        
        # 回退到普通优化版本
        print("\n回退到普通优化版本...")
        from crack import main
        main()
