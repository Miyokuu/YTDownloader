# -*- coding: UTF-8 -*-
"""Module containing all classes to download YouTube content."""
from __future__ import annotations
from typing import Any, Optional, Callable
from pathlib import Path

import webbrowser
import PySimpleGUI as sg
from pytube import YouTube, Playlist, Stream

from .downloader_base import YouTubeDownloader
from .download_option import DownloadOption


# -------------------- defining download options
LD: DownloadOption = DownloadOption("360p", "video", True, None)
HD: DownloadOption = DownloadOption("720p", "video", True, None)
AUDIO: DownloadOption = DownloadOption(None, "audio", False, "128kbps")

# -------------------- defining popups
DOWNLOAD_DIR_POPUP: Callable[[], Any] = lambda: sg.Popup(
    "Please select a download directory", title="Info"
)
RESOLUTION_UNAVAILABLE_POPUP: Callable[[], Any] = lambda: sg.Popup(
    "This resolution is resolution unavailable.", title="Info"
)


class PlaylistDownloader(YouTubeDownloader):
    """Class that contains and creates the window and necessary methods to download a YouTube playlist."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.playlist: Playlist = Playlist(self.url)

        # -------------------- binding the playlists (list of streams) to corresponding download option
        hd_list: list[Stream] = self.get_playlist(HD)
        ld_list: list[Stream] = self.get_playlist(LD)
        audio_list: list[Stream] = self.get_playlist(AUDIO)
        self.select_dict: dict[DownloadOption, Optional[list[Stream]]] = {
            HD: hd_list if len(hd_list) == self.playlist.length else None,
            LD: ld_list if len(ld_list) == self.playlist.length else None,
            AUDIO: ld_list if len(audio_list) == self.playlist.length else None,
        }

        # -------------------- defining layouts
        info_tab: list[list[sg.Text]] = [
            [sg.Text("URL:"), sg.Text(self.url, enable_events=True, key="-URL-")],
            [sg.Text("Title:"), sg.Text(self.playlist.title)],
            [sg.Text("Videos:"), sg.Text(self.playlist.length)],  # type: ignore
            [sg.Text("Views:"), sg.Text(f"{self.playlist.views:,}")],
            [
                sg.Text("Owner:"),
                sg.Text(self.playlist.owner, enable_events=True, key="-OWNER-"),
            ],
            [sg.Text("Last updated:"), sg.Text(self.playlist.last_updated)],
        ]

        download_all_tab: list[list[sg.Text | sg.Input | sg.Frame]] = [
            [
                sg.Text("Download Folder"),
                sg.Input(size=(53, 1), enable_events=True, key="-FOLDER-"),
                sg.FolderBrowse(),
            ],
            [
                sg.Frame(
                    "Highest resolution",
                    [
                        [
                            sg.Button("Download All", key="-HD-"),
                            sg.Text(HD.RESOLUTION),  # type: ignore
                            sg.Text(self.get_playlist_size(HD)),
                        ]
                    ],
                )
            ],
            [
                sg.Frame(
                    "Lowest resolution",
                    [
                        [
                            sg.Button("Download All", key="-LD-"),
                            sg.Text(LD.RESOLUTION),  # type: ignore
                            sg.Text(self.get_playlist_size(LD)),
                        ]
                    ],
                )
            ],
            [
                sg.Frame(
                    "Audio only",
                    [
                        [
                            sg.Button("Download All", key="-AUDIOALL-"),
                            sg.Text(self.get_playlist_size(AUDIO)),
                        ]
                    ],
                )
            ],
            [sg.VPush()],
            [
                sg.Text(
                    "",
                    key="-COMPLETED-",
                    size=(57, 1),
                    justification="c",
                    font="underline",
                )
            ],
            [
                sg.Progress(
                    self.playlist.length,
                    orientation="h",
                    size=(20, 20),
                    key="-DOWNLOADPROGRESS-",
                    expand_x=True,
                    bar_color="Black",
                )
            ],
        ]

        self.main_layout: list[list[sg.TabGroup]] = [
            [
                sg.TabGroup(
                    [
                        [
                            sg.Tab("info", info_tab),
                            sg.Tab("download all", download_all_tab),
                        ]
                    ]
                )
            ]
        ]

        self.download_window: sg.Window = sg.Window(
            "Youtube Downloader", self.main_layout, modal=True
        )

    def get_playlist(self, download_option: DownloadOption) -> list[Stream]:
        """Returns a list of the streams to the corresponding download option."""
        return [
            video.streams.filter(
                resolution=download_option.RESOLUTION,
                type=download_option.TYPE,
                progressive=download_option.PROGRESSIVE,
                abr=download_option.ABR,
            ).first()
            for video in self.playlist.videos
        ]  # type: ignore

    def get_playlist_size(self, download_option: DownloadOption) -> str:
        """Returns the size of the playlist to the corresponding download option."""
        if self.select_dict[download_option] is None:
            return "Unavailable"
        return f"{round(sum(video.filesize for video in self.select_dict[download_option]) / 1048576,1,)} MB"  # type: ignore

    def create_window(self) -> None:
        # -------------------- download window event loop
        while True:
            event, values = self.download_window.read()  # type: ignore
            try:
                self.folder: str = values["-FOLDER-"]
            except TypeError:
                break

            if event == sg.WIN_CLOSED:
                break

            if event == "-URL-":
                webbrowser.open(self.url)

            if event == "-OWNER-":
                webbrowser.open(self.playlist.owner_url)

            if event == "-HD-":
                self.download(HD)

            if event == "-LD-":
                self.download(LD)

            if event == "-AUDIOALL-":
                self.download(AUDIO)

        self.download_window.close()

    def download(self, download_option: DownloadOption) -> None:
        if self.select_dict[download_option] is None:
            RESOLUTION_UNAVAILABLE_POPUP()
            return

        if not self.folder:
            DOWNLOAD_DIR_POPUP()
            return

        download_dir: Path = self.rename_dir(
            self.folder,
            self.remove_forbidden_characters(self.playlist.title),
        )

        download_counter: int = 0
        for video in self.playlist.videos:
            (
                video.streams.filter(
                    resolution=download_option.RESOLUTION,
                    type=download_option.TYPE,
                    progressive=download_option.PROGRESSIVE,
                    abr=download_option.ABR,
                )
                .first()
                .download(  # type: ignore
                    output_path=download_dir,  # type: ignore
                    filename=f"{self.remove_forbidden_characters(video.title)}.mp4",
                )
            )
            download_counter += 1
            self.download_window["-DOWNLOADPROGRESS-"].update(download_counter)  # type: ignore
            self.download_window["-COMPLETED-"].update(
                f"{download_counter} of {self.playlist.length}"  # type: ignore
            )
        self.__download_complete()

    def __download_complete(self) -> None:
        """Helper method that resets the download progressbar and notifies the user when the download has finished."""
        self.download_window["-DOWNLOADPROGRESS-"].update(0)  # type: ignore
        self.download_window["-COMPLETED-"].update("")  # type: ignore
        sg.Popup("Download completed")


class VideoDownloader(YouTubeDownloader):
    """Class that contains and creates the window and necessary methods to download a YouTube video."""

    __slots__: tuple[str, ...] = (
        "url",
        "video",
        "select_dict",
        "download_window",
        "folder",
    )

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.video: YouTube = YouTube(
            self.url,
            on_progress_callback=self.__progress_check,
            on_complete_callback=self.__on_complete,
        )

        # -------------------- binding videos to corresponding download option
        self.select_dict: dict[DownloadOption, Optional[Stream]] = {
            HD: self.get_video(HD),
            LD: self.get_video(LD),
            AUDIO: self.get_video(AUDIO),
        }

        # -------------------- defining layouts
        info_tab: list[list[sg.Text | sg.Multiline]] = [
            [sg.Text("URL:"), sg.Text(self.url, enable_events=True, key="-URL-")],
            [sg.Text("Title:"), sg.Text(self.video.title)],
            [sg.Text("Length:"), sg.Text(f"{round(self.video.length / 60,2)} minutes")],
            [sg.Text("Views:"), sg.Text(f"{self.video.views:,}")],
            [
                sg.Text("Creator:"),
                sg.Text(self.video.author, enable_events=True, key="-CREATOR-"),
            ],
            [
                sg.Text("Thumbnail:"),
                sg.Text(self.video.thumbnail_url, enable_events=True, key="-THUMB-"),
            ],
            [
                sg.Text("Description:"),
                sg.Multiline(
                    self.video.description,
                    size=(40, 20),
                    no_scrollbar=True,
                    disabled=True,
                ),
            ],
        ]

        download_tab: list[
            list[sg.Text | sg.Input | sg.Button]
            | list[sg.Text | sg.Input | sg.Frame | sg.Progress]
        ] = [
            [
                sg.Text("Download Folder"),
                sg.Input(size=(27, 1), enable_events=True, key="-FOLDER-"),
                sg.FolderBrowse(),
            ],
            [
                sg.Frame(
                    "Highest resolution",
                    [
                        [
                            sg.Button("Download", key="-HD-"),
                            sg.Text(HD.RESOLUTION),  # type: ignore
                            sg.Text(self.get_video_size(HD)),
                        ]
                    ],
                )
            ],
            [
                sg.Frame(
                    "Lowest resolution",
                    [
                        [
                            sg.Button("Download", key="-LD-"),
                            sg.Text(LD.RESOLUTION),  # type: ignore
                            sg.Text(self.get_video_size(LD)),
                        ]
                    ],
                )
            ],
            [
                sg.Frame(
                    "Audio only",
                    [
                        [
                            sg.Button("Download", key="-AUDIO-"),
                            sg.Text(self.get_video_size(AUDIO)),
                        ]
                    ],
                )
            ],
            [sg.VPush()],
            [
                sg.Text(
                    "",
                    key="-COMPLETED-",
                    size=(40, 1),
                    justification="c",
                    font="underline",
                )
            ],
            [
                sg.Progress(
                    100,
                    orientation="h",
                    size=(20, 20),
                    key="-DOWNLOADPROGRESS-",
                    expand_x=True,
                    bar_color="Black",
                )
            ],
        ]

        main_layout: list[list[sg.TabGroup]] = [
            [
                sg.TabGroup(
                    [[sg.Tab("info", info_tab), sg.Tab("download", download_tab)]]
                )
            ]
        ]

        self.download_window: sg.Window = sg.Window(
            "Youtube Downloader", main_layout, modal=True
        )

    def get_video(self, download_option: DownloadOption) -> Optional[Stream]:
        """Returns the stream to the corresponding download option."""
        return self.video.streams.filter(
            resolution=download_option.RESOLUTION,
            type=download_option.TYPE,
            progressive=download_option.PROGRESSIVE,
            abr=download_option.ABR,
        ).first()

    def get_video_size(self, download_option: DownloadOption) -> str:
        """Returns the size of the video to the corresponding download option."""
        if self.select_dict[download_option] is None:
            return "Unavailable"
        return f"{round(self.select_dict[download_option].filesize / 1048576, 1)} MB"  # type: ignore

    def create_window(self) -> None:
        # -------------------- download window event loop
        while True:
            event, values = self.download_window.read()  # type: ignore
            try:
                self.folder: str = values["-FOLDER-"]
            except TypeError:
                break

            if event == sg.WIN_CLOSED:
                break

            if event == "-URL-":
                webbrowser.open(self.url)

            if event == "-CREATOR-":
                webbrowser.open(self.video.channel_url)

            if event == "-THUMB-":
                webbrowser.open(self.video.thumbnail_url)

            if event == "-HD-":
                self.download(HD)

            if event == "-LD-":
                self.download(LD)

            if event == "-AUDIO-":
                self.download(AUDIO)

        self.download_window.close()

    def download(self, download_option: DownloadOption) -> None:
        if self.select_dict[download_option] is None:
            RESOLUTION_UNAVAILABLE_POPUP()
            return

        if not self.folder:
            DOWNLOAD_DIR_POPUP()
            return
        (
            self.select_dict[download_option].download(  # type: ignore
                output_path=self.folder,
                filename=f"{self.rename_file(self.folder, self.remove_forbidden_characters(self.video.title))}.mp4",
            )
        )

    def __progress_check(
        self, stream: Any, chunk: bytes, bytes_remaining: int
    ) -> None:  # parameters are necessary
        """Helper method that updated the progress bar when progress in the video download was made."""
        self.download_window["-DOWNLOADPROGRESS-"].update(
            100 - round(bytes_remaining / stream.filesize * 100)  # type: ignore
        )
        self.download_window["-COMPLETED-"].update(
            f"{100 - round(bytes_remaining / stream.filesize * 100)}% completed"  # type: ignore
        )

    def __on_complete(
        self, stream: Any, file_path: Optional[str]
    ) -> None:  # parameters are necessary
        """Helper method that resets the progress bar when the video download has finished."""
        self.download_window["-DOWNLOADPROGRESS-"].update(0)  # type: ignore
        self.download_window["-COMPLETED-"].update("")  # type: ignore
        sg.Popup("Download completed")
