"""B站视频下载工具

使用 you-get 库下载 B 站视频，支持获取视频信息、下载和自动合并音视频功能。
配置从 .env 文件读取环境变量。
"""

from __future__ import annotations

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List

# 尝试加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class BilibiliDownloader:
    """B站视频下载器"""

    def __init__(self, download_dir: str = None):
        """
        初始化下载器
        
        :param download_dir: 下载目录，优先使用环境变量 DOWNLOAD_DIR
        """
        # 优先使用环境变量，其次使用参数，最后使用默认值
        env_dir = os.getenv("DOWNLOAD_DIR")
        if download_dir is not None:
            self.download_dir = Path(download_dir)
        elif env_dir:
            self.download_dir = Path(env_dir)
        else:
            self.download_dir = Path("./downloads")
        
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _is_ffmpeg_available(self) -> bool:
        """检查 ffmpeg 是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _is_audio_only(self, file_path: str) -> bool:
        """
        使用 ffmpeg 检查文件是否为纯音频文件
        
        :param file_path: 文件路径
        :return: 是否为纯音频文件
        """
        if not self._is_ffmpeg_available():
            return False
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", file_path],
                capture_output=True,
                text=True,
                stderr=subprocess.STDOUT
            )
            has_video = "Video:" in result.stdout
            has_audio = "Audio:" in result.stdout
            return has_audio and not has_video
        except Exception:
            return False

    def _find_video_audio_files(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """
        在下载目录中查找分离的视频和音频文件
        
        B站DASH格式会将音视频分开下载，可能都是.mp4扩展名：
        - [00].mp4 通常是视频（较小）
        - [01].mp4 通常是音频（较大，包含音轨）
        
        如果 ffmpeg 可用，会使用 ffmpeg 进行准确判断。
        
        :param title: 视频标题（用于匹配文件名）
        :return: (视频文件路径, 音频文件路径)
        """
        video_file = None
        audio_file = None
        mp4_files = []
        
        for file in self.download_dir.iterdir():
            filename = file.name.lower()
            title_lower = title.lower()
            
            # 检查文件名是否包含标题
            if title_lower.replace(' ', '') in filename.replace(' ', '') or \
               title_lower[:20] in filename[:20]:
                
                if file.suffix in ['.m4a', '.mp3', '.aac']:
                    audio_file = str(file)
                elif file.suffix in ['.mp4', '.flv', '.webm']:
                    mp4_files.append((str(file), file.stat().st_size))
        
        # 如果有多个MP4文件，使用ffmpeg判断或按大小排序
        if len(mp4_files) >= 2:
            if self._is_ffmpeg_available():
                # 使用ffmpeg进行准确判断
                for file_path, _ in mp4_files:
                    if self._is_audio_only(file_path):
                        audio_file = file_path
                    else:
                        video_file = file_path
            else:
                # 回退到按大小排序
                mp4_files.sort(key=lambda x: x[1])
                video_file = mp4_files[0][0]  # 较小的是视频
                audio_file = mp4_files[-1][0]  # 较大的是音频
        elif len(mp4_files) == 1:
            video_file = mp4_files[0][0]
        
        return video_file, audio_file

    def _merge_video_audio(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """
        使用 ffmpeg 合并视频和音频
        
        :param video_path: 视频文件路径
        :param audio_path: 音频文件路径
        :param output_path: 输出文件路径
        :return: 是否成功
        """
        try:
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "copy",
                "-y",  # 覆盖输出文件
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
        except Exception as e:
            print(f"合并失败: {e}")
            return False

    def _cleanup_separated_files(self, video_path: str, audio_path: str) -> None:
        """清理分离的视频和音频文件"""
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            print(f"清理文件失败: {e}")

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取视频信息
        
        :param url: B站视频链接
        :return: 视频信息字典，包含标题、时长、画质等
        """
        try:
            result = subprocess.run(
                ["you-get", "-i", url],
                capture_output=True,
                text=True,
                cwd=str(self.download_dir)
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout
            info = {}
            
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('title:'):
                    info['title'] = line.split(':', 1)[1].strip()
                elif line.startswith('type:'):
                    info['type'] = line.split(':', 1)[1].strip()
                elif line.startswith('size:'):
                    info['size'] = line.split(':', 1)[1].strip()
                elif line.startswith('duration:'):
                    info['duration'] = line.split(':', 1)[1].strip()
                elif 'streams' in line.lower() and 'available' in line.lower():
                    info['has_streams'] = True
            
            return info if info else None
            
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None

    def download_video(
        self, 
        url: str, 
        quality: str = "best",
        output_filename: Optional[str] = None,
        auto_merge: bool = True
    ) -> Tuple[bool, str]:
        """
        下载视频
        
        :param url: B站视频链接
        :param quality: 画质选择（旧版you-get默认使用最佳画质）
        :param output_filename: 自定义输出文件名
        :param auto_merge: 是否自动合并分离的音视频
        :return: (是否成功, 保存路径或错误信息)
        """
        try:
            cmd = ["you-get", url, "-o", str(self.download_dir)]
            
            if output_filename:
                cmd.extend(["-O", output_filename])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.download_dir)
            )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                return False, f"下载失败: {error_msg}"
            
            # 获取视频信息用于合并
            video_info = self.get_video_info(url)
            title = video_info.get('title', '') if video_info else output_filename or "video"
            
            # 尝试自动合并
            if auto_merge and self._is_ffmpeg_available():
                video_file, audio_file = self._find_video_audio_files(title)
                
                if video_file and audio_file:
                    # 创建合并后的输出路径
                    merged_path = str(self.download_dir / f"{title}_merged.mp4")
                    
                    if self._merge_video_audio(video_file, audio_file, merged_path):
                        self._cleanup_separated_files(video_file, audio_file)
                        return True, merged_path
                    else:
                        return True, str(self.download_dir)
                elif video_file:
                    # 只有视频文件（可能已包含音频）
                    return True, video_file
            
            # 解析输出获取保存路径
            output = result.stdout
            for line in output.split('\n'):
                if "Saving to" in line:
                    save_path = line.split("Saving to")[1].strip()
                    return True, str(self.download_dir / save_path)
            
            return True, str(self.download_dir)
                
        except FileNotFoundError:
            return False, "未找到 you-get，请先安装: pip install you-get"
        except Exception as e:
            return False, f"下载异常: {str(e)}"

    def download_audio_only(self, url: str, progress_callback=None) -> Tuple[bool, str]:
        """
        仅下载音频文件（最终只保留音频文件，删除视频和xml等临时文件）
        
        :param url: B站视频链接
        :param progress_callback: 进度回调函数，接收进度百分比(0-100)
        :return: (是否成功, 保存路径或错误信息)
        """
        try:
            video_info = self.get_video_info(url)
            title = video_info.get('title', 'audio') if video_info else "audio"
            print(f"[DEBUG] 视频标题: {title}")
            print(f"[DEBUG] 下载目录: {self.download_dir}")
            
            # 先下载视频（使用Popen实时获取进度）
            cmd = ["you-get", url, "-o", str(self.download_dir)]
            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
            
            # 使用Popen实时读取输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.download_dir),
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时解析进度
            import re
            progress_pattern = re.compile(r'(\d{1,3})%')
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    print(f"[DEBUG] you-get: {line.strip()}")
                    # 解析进度
                    match = progress_pattern.search(line)
                    if match and progress_callback:
                        try:
                            progress = int(match.group(1))
                            progress_callback(progress)
                        except ValueError:
                            pass
            
            # 获取剩余输出和错误
            stdout, stderr = process.communicate()
            return_code = process.returncode
            
            print(f"[DEBUG] you-get 返回码: {return_code}")
            if stdout:
                print(f"[DEBUG] you-get 输出:\n{stdout}")
            if stderr:
                print(f"[DEBUG] you-get 错误输出:\n{stderr}")
            
            if return_code != 0:
                error_msg = stderr if stderr else stdout
                return False, f"下载失败: {error_msg}"
            
            # 列出下载目录内容
            files = list(self.download_dir.iterdir())
            print(f"[DEBUG] 下载目录中的文件:")
            for f in files:
                print(f"  - {f.name} ({f.stat().st_size} bytes)")
            
            # 查找音频和视频文件
            video_file, audio_file = self._find_video_audio_files(title)
            print(f"[DEBUG] 找到视频文件: {video_file}")
            print(f"[DEBUG] 找到音频文件: {audio_file}")
            
            final_audio_path = None
            
            if audio_file:
                print(f"[DEBUG] 使用已有的音频文件")
                final_audio_path = audio_file
            elif video_file and self._is_ffmpeg_available():
                print(f"[DEBUG] 从视频中提取音频")
                audio_output = str(self.download_dir / f"{title}.mp3")
                cmd = [
                    "ffmpeg",
                    "-i", video_file,
                    "-q:a", "0",
                    "-map", "a",
                    "-y",
                    audio_output
                ]
                extract_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                print(f"[DEBUG] ffmpeg 返回码: {extract_result.returncode}")
                if extract_result.returncode != 0 and extract_result.stderr:
                    print(f"[DEBUG] ffmpeg 错误: {extract_result.stderr[:200]}")
                if extract_result.returncode == 0:
                    final_audio_path = audio_output
                    print(f"[DEBUG] 音频提取成功: {audio_output}")
            else:
                print(f"[DEBUG] 没有找到音频文件，ffmpeg可用: {self._is_ffmpeg_available()}")
            
            # 清理所有临时文件（视频、xml等），保留音频文件
            print(f"[DEBUG] 开始清理临时文件，保留音频: {final_audio_path}")
            self._cleanup_temp_files(title, keep_file=final_audio_path)
            
            # 再次列出目录内容
            files = list(self.download_dir.iterdir())
            print(f"[DEBUG] 清理后的文件:")
            for f in files:
                print(f"  - {f.name} ({f.stat().st_size} bytes)")
            
            if final_audio_path:
                return True, final_audio_path
            
            return True, str(self.download_dir)
                
        except FileNotFoundError:
            return False, "未找到 you-get，请先安装: pip install you-get"
        except Exception as e:
            return False, f"下载异常: {str(e)}"

    def _cleanup_temp_files(self, title: str, keep_file: Optional[str] = None) -> None:
        """
        清理下载目录中的临时文件（视频、xml等），保留指定的文件
        
        :param title: 视频标题
        :param keep_file: 需要保留的文件路径
        """
        title_lower = title.lower()
        
        for file in self.download_dir.iterdir():
            file_path = str(file)
            filename = file.name.lower()
            
            # 保留指定的文件
            if keep_file and file_path == keep_file:
                continue
            
            # 检查文件名是否匹配当前下载的视频
            if title_lower.replace(' ', '') in filename.replace(' ', '') or \
               title_lower[:20] in filename[:20]:
                
                # 删除其他文件（视频、xml等）
                try:
                    os.remove(file)
                    print(f"[DEBUG] 已删除临时文件: {file.name}")
                except Exception as e:
                    print(f"清理临时文件失败 {file.name}: {e}")


# 示例用法
if __name__ == "__main__":
    downloader = BilibiliDownloader()
    
    # 测试视频链接（请替换为实际视频链接）
    test_url = "https://www.bilibili.com/video/BV1NsXxB2Ewh/?spm_id_from=333.337.search-card.all.click&vd_source=e0789e9b57c30e803230723fe7559054"
    
    # 获取视频信息
    info = downloader.get_video_info(test_url)
    if info:
        print("视频信息:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    # 下载视频（自动合并音视频）
    # success, path = downloader.download_video(test_url)
    # if success:
    #     print(f"下载成功，保存到: {path}")
    # else:
    #     print(f"下载失败: {path}")
    
    # 仅下载音频
    success, path = downloader.download_audio_only(test_url)
    if success:
        print(f"音频下载成功，保存到: {path}")
    else:
        print(f"音频下载失败: {path}")
