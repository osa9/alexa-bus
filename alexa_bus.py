import logging
import urllib.request
from bs4 import BeautifulSoup


# 小田急バスのリアルタイム運行状況のURL(サンプルは三鷹市役所前 → 三鷹駅)
BUS_SCHEDULE_URL = 'http://www.odakyubus-navi.com/blsys/loca?VID=lsc&EID=nt&DSMK=46&ASMK=148'


# Echo Spotの画面に表示される背景画像(480x480のPNG/JPG)
IMAGE_URL = 'https://example.com/example.png'


def get_bus_schedule(url):
    """
    小田急バスのリアルタイム運行状況を取得する
    """
    logging.info("Retrieving URL: {}".format(url))
    content = urllib.request.urlopen(url).read().decode('shift_jisx0213')
    soup = BeautifulSoup(content, "html.parser")

    # エラーメッセージがある時(バスが終了している時も含む)
    errors = soup.select('.errorCntTxt')
    if len(list(errors)) > 0:
        message = errors[0].contents[0]
        logging.warn("Error: ".format(message))
        raise Exception(message)

    # 区間を取得する
    section = soup.select('.mt10')[0].contents[0].split('：')[1]

    # ダイヤをパースする
    result = []
    for bus_info in soup.select('.resultTbl tr')[1:]:
        res = list(map(lambda col: col.string, bus_info.find_all('td')))
        # のりば名が無いパターンの時(のりばが一個しか無い時等)
        if len(res) == 6:
            res = res[:2] + [None] + res[2:]

        info = {
            'scheduled_arrival': res[0],  # 時刻表上の到着時刻(ex 10:00)
            'estimated_arrival': res[1],  # 予想到着時刻(ex 10:02)
            'bus_stop': res[2],  # 乗り場 (ない時はNone)
            'destination': res[3],  # 行き先 (ex 【鷹５４】三鷹駅)
            'type': res[4],  # 車両 (ex ノンステップ)
            'status': res[5],  # 運行状況 (ex 約5分で到着します。, まもなく到着します)
            'destination_arrival': res[6]  # 目的地到着（予測） (ex 10:15)
        }

        result += [info]

    return section, result


def bus(event, context):
    """
    Alexaから呼び出されるハンドラー
    """
    logging.info(event)

    # もしバス停名を指定したければ使う
    # busStopName = event['request']['intent']['slots']['BusStop']

    # スケジュールを取得してメッセージを作成
    try:
        section, schedules = get_bus_schedule(BUS_SCHEDULE_URL)

        # しゃべるメッセージ
        speech_message = '{}行きのバスは{}'.format(schedules[0]['destination'], schedules[0]['status'])
        if len(schedules) > 1:
            speech_message += '次は{}'.format(schedules[1]['status'])

        # 表示するメッセージ(タイトルと本文)
        display_title = section
        content = '<br/>'.join(map(lambda s: '{}:{}'.format(s['destination'],s['status']), schedules[:3]))
        display_message = '<font size="2">{}</font>'.format(content)
    except Exception as e:
        print(e)
        speech_message = 'エラーが発生しました'
        display_title = 'エラー'
        display_message = speech_message

    # レスポンスを組み立てて返却する
    response = {
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': speech_message,
            },
            'directives': [
                {
                    'type': 'Display.RenderTemplate',
                    'template': {
                        'type': 'BodyTemplate1',  # テンプレートの種類
                        'token': 'TimeTable1',  # 画面の名前(ページ遷移で使う)
                        'title': display_title,  # タイトル
                        'backgroundImage': {  # 背景画像(省略可)
                            "contentDescription": "string",
                            "sources": [
                                {
                                    "url": IMAGE_URL,
                                }
                            ]
                        },
                        'textContent': {  # 本文
                            'primaryText': {
                                'type': 'RichText',
                                'text': display_message
                            }
                        }
                    }
                }
            ]
        }
    }

    return response


# テスト用
if __name__ == '__main__':
    print(bus(None, None))
