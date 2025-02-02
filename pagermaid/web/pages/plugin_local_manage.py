from amis import InputText, Switch, Card, CardsCRUD, PageSchema, Page

card = Card(
    header=Card.Header(
        title='$name',
        avatarText='$name',
        avatarTextClassName='overflow-hidden'
    ),
    actions=[],
    toolbar=[
        Switch(
            name='enable',
            value='${status}',
            onText='启用',
            offText='禁用',
            onEvent={
                'change': {
                    'actions': [
                        {
                            'actionType': 'ajax',
                            'args': {
                                'api': {
                                    'url': '/pagermaid/api/set_local_plugin_status',
                                    'method': 'post'
                                },
                                'messages': {
                                    'success': '成功${IF(event.data.value, "开启", "禁用")}了 ${name}',
                                    'failed': '操作失败'
                                },
                                'status': '${event.data.value}',
                                'plugin': '${name}'
                            }
                        },
                    ]
                }
            }
        )
    ]
)
cards_curd = CardsCRUD(
    mode='cards',
    title='',
    syncLocation=False,
    api='/pagermaid/api/get_local_plugins',
    loadDataOnce=True,
    source='${rows | filter:name:match:keywords_name}',
    filter={
        'body': [
            InputText(name='keywords_name', label='插件名')
        ]
    },
    perPage=12,
    autoJumpToTopOnPagerChange=True,
    placeholder='暂无插件信息',
    footerToolbar=['switch-per-page', 'pagination'],
    columnsCount=3,
    card=card
)
page = PageSchema(
    url='/plugins/local',
    icon='fa fa-database',
    label='本地插件管理',
    schema=Page(title='本地插件管理', body=cards_curd)
)
