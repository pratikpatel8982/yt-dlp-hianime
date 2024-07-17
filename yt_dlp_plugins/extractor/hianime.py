import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, clean_html, get_element_by_class


class HiAnimeIE(InfoExtractor):
    _VALID_URL = r'https?://hianime\.to/(?:watch/)?(?P<slug>[^/?]+)(?:-\d+)?-(?P<playlist_id>\d+)(?:\?ep=(?P<episode_id>\d+))?$'

    _TESTS = [
        {
            'url': 'https://hianime.to/demon-slayer-kimetsu-no-yaiba-hashira-training-arc-19107',
            'info_dict': {
                'id': '19107',
                'title': 'Demon Slayer: Kimetsu no Yaiba Hashira Training Arc',
            },
            'playlist_count': 8,
        },
        {
            'url': 'https://hianime.to/watch/demon-slayer-kimetsu-no-yaiba-hashira-training-arc-19107?ep=124260',
            'info_dict': {
                'id': '124260',
                'title': 'To Defeat Muzan Kibutsuji',
                'ext': 'mp4',
                'series': 'Demon Slayer: Kimetsu no Yaiba Hashira Training Arc',
                'series_id': '19107',
                'episode': 'To Defeat Muzan Kibutsuji',
                'episode_number': 1,
                'episode_id': '124260',
            },
        },
        {
            'url': 'https://hianime.to/the-eminence-in-shadow-17473',
            'info_dict': {
                'id': '17473',
                'title': 'The Eminence in Shadow',
            },
            'playlist_count': 20,
        },
        {
            'url': 'https://hianime.to/watch/the-eminence-in-shadow-17473?ep=94440',
            'info_dict': {
                'id': '94440',
                'title': 'The Hated Classmate',
                'ext': 'mp4',
                'series': 'The Eminence in Shadow',
                'series_id': '17473',
                'episode': 'The Hated Classmate',
                'episode_number': 1,
                'episode_id': '94440',
            },
        },
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anime_title = None
        self.episode_list = {}
        self.language = {
            'sub': 'ja',
            'dub': 'en',
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        playlist_id = mobj.group('playlist_id')
        episode_id = mobj.group('episode_id')
        slug = mobj.group('slug')

        if episode_id:
            return self._extract_episode(slug, playlist_id, episode_id, url)
        elif playlist_id:
            return self._extract_playlist(slug, playlist_id, url)
        else:
            raise ExtractorError('Unsupported URL format')

    def _extract_custom_m3u8_formats(self, m3u8_url, episode_id, server_type=None):
        formats = self._extract_m3u8_formats(m3u8_url, episode_id, 'mp4', entry_protocol='m3u8_native', fatal=False, note='Downloading M3U8 Information')

        for f in formats:
            height = f.get('height')
            f['format_id'] = f'{server_type.upper()}{height}p'
            f['language'] = self.language[server_type]
        return formats

    def _get_anime_title(self, slug, playlist_id):
        if not self.anime_title:
            webpage = self._download_webpage(f'https://hianime.to/{slug}-{playlist_id}', playlist_id, note='Fetching Anime Title')
            self.anime_title = get_element_by_class('film-name dynamic-name', webpage)
        return self.anime_title

    def _extract_playlist(self, slug, playlist_id, url):
        anime_title = self._get_anime_title(slug, playlist_id)
        playlist_url = f'https://hianime.to/ajax/v2/episode/list/{playlist_id}'
        playlist_data = self._download_json(playlist_url, playlist_id, note='Fetching Episode List')
        episodes = self._get_elements_by_tag_and_attrib(playlist_data['html'], tag='a', attribute='class', value='ssl-item  ep-item')

        entries = []
        for episode in episodes:
            episode_html = episode.group(0)

            # Extract episode details
            title_match = re.search(r'title="([^"]+)"', episode_html)
            data_number_match = re.search(r'data-number="([^"]+)"', episode_html)
            data_id_match = re.search(r'data-id="([^"]+)"', episode_html)
            href_match = re.search(r'href="([^"]+)"', episode_html)

            title = clean_html(title_match.group(1)) if title_match else None
            data_number = data_number_match.group(1) if data_number_match else None
            data_id = data_id_match.group(1) if data_id_match else None
            url = f'https://hianime.to{href_match.group(1)}' if href_match else None

            # Add episode details to episode_list
            self.episode_list[data_id] = {
                'title': title,
                'number': int(data_number),
                'url': url,
            }

            # Prepare entry for playlist result
            entries.append(self.url_result(
                url,
                ie=self.ie_key(),
                video_id=data_id,
                video_title=title,
            ))

        return self.playlist_result(entries, playlist_id, anime_title)

    def _extract_episode(self, slug, playlist_id, episode_id, url):
        anime_title = self._get_anime_title(slug, playlist_id)
        episode_data = self.episode_list.get(episode_id)
        if not episode_data:
            self._extract_playlist(slug, playlist_id, url)
            episode_data = self.episode_list.get(episode_id)
        if not episode_data:
            raise ExtractorError(f'Episode data for episode_id {episode_id} not found')

        # Extract episode information and formats
        servers_url = f'https://hianime.to/ajax/v2/episode/servers?episodeId={episode_id}'
        servers_data = self._download_json(servers_url, episode_id, note='Fetching Server IDs')

        formats = []
        subtitles = {}

        for server_type in ['sub', 'dub']:
            server_items = self._get_elements_by_tag_and_attrib(servers_data['html'], tag='div', attribute='data-type', value=f'{server_type}', escape_value=False)
            server_id = next((re.search(r'data-id="([^"]+)"', item.group(0)).group(1) for item in server_items if re.search(r'data-id="([^"]+)"', item.group(0))), None)

            if not server_id:
                break

            sources_url = f'https://hianime.to/ajax/v2/episode/sources?id={server_id}'
            sources_data = self._download_json(sources_url, episode_id, note=f'Getting {server_type.upper()}BED Episode Information')
            link = sources_data.get('link')

            if not link:
                break

            sources_id_match = re.search(r'/embed-2/[^/]+/([^?]+)\?', link)
            sources_id = sources_id_match.group(1) if sources_id_match else None

            if not sources_id:
                break

            video_url = f'https://megacloud.tv/embed-2/ajax/e-1/getSources?id={sources_id}'
            video_data = self._download_json(video_url, episode_id, note=f'Getting {server_type.upper()}BED Episode Formats')
            sources = video_data.get('sources', [])

            for source in sources:
                file_url = source.get('file')

                if not (file_url and file_url.endswith('.m3u8')):
                    break

                extracted_formats = self._extract_custom_m3u8_formats(file_url, episode_id, server_type)
                # print(extracted_formats)
                formats.extend(extracted_formats)

            tracks = video_data.get('tracks', [])

            for track in tracks:
                if track.get('kind') == 'captions':
                    file_url = track.get('file')
                    language = track.get('label')
                    if language == 'English':
                        language = f'{language} {server_type.capitalize()}bed'

                    if not file_url:
                        break

                    if (language) not in subtitles:
                        subtitles[language] = []

                    subtitles[language].append({
                        'url': file_url,
                    })
        subtitles = dict(sorted(subtitles.items()))

        return {
            'id': episode_id,
            'title': episode_data['title'],
            'formats': formats,
            'subtitles': subtitles,
            'series': anime_title,
            'series_id': playlist_id,
            'episode': episode_data['title'],
            'episode_number': episode_data['number'],
            'episode_id': episode_id,
        }

    def _get_elements_by_tag_and_attrib(self, html, tag=None, attribute=None, value=None, escape_value=True):
        if tag is None:
            tag = r'[a-zA-Z0-9:._-]+'

        if attribute:
            attribute = rf'\s+{re.escape(attribute)}'

        if value:
            value = re.escape(value) if escape_value else value
            value = f'=[\'"]?(?P<value>{value})[\'"]?'

        return list(re.finditer(rf'''(?xs)
            <{tag}
            (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
            {attribute}{value}
            (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
            \s*>
            (?P<content>.*?)
            </{tag}>
        ''', html))
