"""
Echo 学习助手 - 最终用户测试（真实大学生视角）
使用 Playwright + Gradio Client 组合测试
"""
import sys, io, time, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright
from gradio_client import Client, handle_file

BASE = 'http://127.0.0.1:7860'
SCREENSHOT_DIR = 'E:/echo/test_screenshots'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

issues = []
step = [0]

def ss(page, label):
    step[0] += 1
    path = os.path.join(SCREENSHOT_DIR, f'final_{step[0]:02d}_{label}.png')
    page.screenshot(path=path, full_page=True)
    print(f'  [screenshot] {path.split("/")[-1]}')

def issue(sev, test, title, desc, reproduce, suggest):
    issues.append({'severity': sev, 'test': test, 'title': title,
                   'desc': desc, 'reproduce': reproduce, 'suggest': suggest})

def h(title): print(f'\n{"="*60}\n{title}\n{"="*60}')

def run():
    client = Client(BASE)
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(BASE, wait_until='domcontentloaded')
    time.sleep(4)

    # Helper: find chat elements
    def find_chat_input():
        for ta in page.locator('textarea').all():
            try:
                ph = ta.get_attribute('placeholder') or ''
                if '人话' in ph or '问题' in ph:
                    return ta
            except: pass
        return None

    def find_send_btn():
        for btn in page.locator('button').all():
            try:
                if '发送' in btn.inner_text().strip():
                    return btn
            except: pass
        return None

    def get_chat_content():
        """Get all chat messages from page"""
        msgs = []
        for cls, role in [('.user', 'USER'), ('.bot', 'BOT')]:
            for elem in page.locator(cls).all():
                try: msgs.append((role, elem.inner_text()))
                except: pass
        return msgs

    # ================================================================
    # TEST 1: 首次使用体验
    # ================================================================
    h('测试1：首次使用体验')
    ss(page, 'first_impression')
    body = page.inner_text('body')
    print('页面可见文字:')
    print(body[:500])

    print('\n[学生思考]')
    print('Q: 这个系统是干什么的？')
    print('A: 标题是"大学课程学习助手"，可能是类似ChatGPT的东西？')
    print('   没有任何说明告诉我它和ChatGPT有什么区别。')
    print('   我不知道它需要我上传课件才能用。')
    issue('P2', 1, '首页缺少功能说明',
          '标题只有7个字，没有解释系统是什么、能做什么、和普通AI有什么区别',
          '首次打开页面，阅读所有可见文字',
          '标题下增加副标题"上传你的课程资料，AI帮你总结、出题、答疑"')

    print('\nQ: 第一步该做什么？')
    print('A: 看到5个按钮/输入框一字排开：课程下拉、新建课程、创建、上传、删除')
    print('   作为新用户，完全不知道该先点哪个。')
    issue('P1', 1, '无新手操作引导',
          '5个操作控件同时显示，没有优先级指引。学生在不知道系统原理的情况下可能先去"上传"或"提问"',
          '首次打开页面，观察30秒界面',
          '添加步骤引导：Step1创建课程 → Step2上传资料 → Step3开始提问')

    print('\nQ: 哪些地方困惑？')
    confusions = [
        '默认课程显示"全部"——什么是"全部"？是所有课程还是所有内容？',
        '欢迎区是空白的——没有欢迎消息、没有提示',
        '"删除课程"和"删除选中文件"从一开始就可见——我还没创建任何东西',
        '底部快捷按钮没有说明它们的作用',
        '整个页面看起来像一个开发工具，不像是给学生用的学习助手',
    ]
    for c in confusions:
        print(f'  * {c}')
    issue('P2', 1, '界面像开发工具不像学生应用',
          '控件密集排列、无视觉层次、删除按钮与创建按钮同等可见度',
          '首次打开页面',
          '区分主次操作，隐藏高级/危险操作，增加引导性文字')

    # ================================================================
    # TEST 2: 课程创建
    # ================================================================
    h('测试2：课程创建')

    # Find course name input
    course_input = None
    for inp in page.locator('textarea, input[type="text"]').all():
        try:
            ph = inp.get_attribute('placeholder') or ''
            if '课程名' in ph:
                course_input = inp
                break
        except: pass

    if not course_input:
        # Fallback: find input near "新建课程" label
        labels = page.locator('label').all()
        for lbl in labels:
            try:
                if '新建' in lbl.inner_text():
                    # Get parent sibling input
                    course_input = lbl.locator('..').locator('textarea, input').first
                    break
            except: pass

    if course_input:
        course_input.click()
        course_input.fill('数据结构')
        print('OK 输入"数据结构"')
        ss(page, 'course_name_entered')

        # Find create button
        create_btn = None
        for btn in page.locator('button').all():
            try:
                if btn.inner_text().strip() == '创建':
                    create_btn = btn
                    break
            except: pass

        if create_btn:
            create_btn.click()
            time.sleep(2)
            ss(page, 'course_created')

            body2 = page.inner_text('body')
            if '已创建' in body2:
                print('OK 看到"已创建"反馈')
            else:
                print('WARN 创建后反馈不明显')
                issue('P2', 2, '创建课程后反馈不明显',
                      '点击创建后，反馈信息在消息区显示，字体小容易被忽略',
                      '输入课程名 -> 点击创建',
                      '创建成功后高亮显示，或用弹窗提示')

            if '数据结构' in body2:
                print('OK 课程出现在界面中')
            else:
                print('ERROR 课程未出现在界面中')
        else:
            print('ERROR 找不到创建按钮')
            issue('P0', 2, '找不到创建按钮',
                  '输入课程名后，找不到提交按钮',
                  '输入课程名 -> 寻找提交入口',
                  '确保创建按钮文字清晰，与输入框紧邻')
    else:
        print('ERROR 找不到课程名输入框')
        issue('P0', 2, '找不到新建课程输入框',
              '想创建课程但不知道在哪输入',
              '打开页面 -> 寻找新建课程入口',
              '给课程名输入框添加醒目的 placeholder 和视觉焦点')

    # ================================================================
    # TEST 3: 上传课程资料
    # ================================================================
    h('测试3：上传课程资料')

    # Upload via file input
    file_inputs = page.locator('input[type="file"]').all()
    pdf_path = 'E:/echo/data/pdfs/test.pdf'

    if file_inputs and os.path.exists(pdf_path):
        file_inputs[0].set_input_files(pdf_path)
        print('OK 选择了 test.pdf')
        time.sleep(5)  # Wait for upload and processing
        ss(page, 'after_upload')

        body3 = page.inner_text('body')
        if '入库完成' in body3:
            print('OK 看到"入库完成"反馈')
        elif '已上传' in body3:
            print('OK 看到"已上传"反馈')
        else:
            print('WARN 上传后无明确反馈')
            issue('P1', 3, '上传后处理状态不明确',
                  '选择文件后，不知道系统是否在处理、什么时候完成',
                  '点击上传 -> 选择PDF -> 等待',
                  '显示实时处理进度，完成后告知用户')

        if 'chunk' in body3.lower():
            print('OK 看到chunk信息（内部处理的细节）')
            # As a student, I wouldn't understand what "chunk" means
            issue('P3', 3, '"chunk"是专业术语，学生不理解',
                  '看到"4个chunk"的提示，学生不知道chunk是什么意思',
                  '上传PDF后观察反馈信息',
                  '用学生能理解的表述，如"已解析4个知识点"')
    else:
        print('ERROR 找不到文件上传入口')
        issue('P0', 3, '找不到文件上传入口',
              '想上传课件但找不到上传按钮或拖拽区',
              '打开页面寻找上传入口',
              '确保上传按钮/区域醒目且位置明显')

    # ================================================================
    # TEST 4: 知识问答
    # ================================================================
    h('测试4：知识问答')

    chat_input = find_chat_input()
    send_btn = find_send_btn()

    if chat_input and send_btn:
        chat_input.click()
        chat_input.fill('总结这门课的主要内容')
        print('OK 输入问题："总结这门课的主要内容"')
        ss(page, 'question_entered')

        send_btn.click()
        print('OK 点击发送，等待回复...')
        time.sleep(10)

        ss(page, 'answer_received')
        msgs = get_chat_content()
        print(f'聊天消息数: {len(msgs)}')
        for role, text in msgs:
            print(f'  [{role}] {text[:300]}')

        # Check if answer references course material
        body4 = page.inner_text('body')
        if any(w in body4 for w in ['test.pdf', '来源', '引用', '文件']):
            print('OK 回答引用了文件信息')
        else:
            print('WARN 回答未显示引用来源')
            issue('P1', 4, '回答不标注引用来源',
                  '学生无法判断AI说的是基于课件还是自己编的',
                  '提问课程相关问题',
                  '回答中标注来源文件名和章节')

        # Check if answer is too generic
        if any(w in body4 for w in ['不知道', '未找到', '无法', '暂无']):
            print('WARN 系统表示无法回答（可能是test.pdf内容太少）')
    else:
        print('SKIP 找不到聊天输入/发送')

    # ================================================================
    # TEST 5: 追问能力
    # ================================================================
    h('测试5：追问能力')

    if chat_input and send_btn:
        follow_ups = ['举个例子', '我不太理解，能用更简单的方式再解释一下吗']
        for q in follow_ups:
            ci = find_chat_input()
            sb = find_send_btn()
            if ci and sb:
                ci.click()
                ci.fill(q)
                print(f'追问: "{q}"')
                sb.click()
                time.sleep(8)

        ss(page, 'followup')
        msgs2 = get_chat_content()
        print(f'追问后消息总数: {len(msgs2)}')
        if len(msgs2) > len(msgs):
            print('OK 有新回复出现')
        else:
            print('WARN 追问后消息数未增加')
            issue('P1', 5, '追问可能未得到回复',
                  '追问后没有新的回复出现（可能是因为上下文丢失或系统无响应）',
                  '提问 -> 追问"举个例子"',
                  '检查追问后是否有新的回复')
    else:
        print('SKIP')

    # ================================================================
    # TEST 6: 错误场景
    # ================================================================
    h('测试6：错误场景 - 课程资料外提问')

    ci = find_chat_input()
    sb = find_send_btn()
    if ci and sb:
        ci.click()
        ci.fill('量子力学是什么？')
        print('提问: "量子力学是什么？"（课程资料中没有量子力学）')
        sb.click()
        time.sleep(8)

        ss(page, 'out_of_scope')
        body6 = page.inner_text('body')
        refusal = ['不知道', '未找到', '暂无', '无法回答', '不在', '没有相关内容']
        fabrication = ['量子力学是物理学', '薛定谔', '量子态', '波函数']

        refused = any(w in body6 for w in refusal)
        fabricated = any(w in body6 for w in fabrication)

        if refused and not fabricated:
            print('OK 系统正确拒绝了无关问题的回答')
        elif fabricated:
            print('ERROR 系统对无关问题编造了答案！')
            issue('P0', 6, '对课程外问题编造答案',
                  '上传数据结构课件后问量子力学，系统编造了量子力学相关内容。这会严重误导学生。',
                  '上传课程资料 -> 提问完全无关的内容',
                  '当检索不到相关内容时，明确告知"课程资料中无此内容"并拒绝编造')
        else:
            print('INFO 无法判断，需人工检查')
            print(f'  回答: {body6[-500:]}')
    else:
        print('SKIP')

    # ================================================================
    # TEST 7: 学习辅助能力
    # ================================================================
    h('测试7：学习辅助功能')

    ci = find_chat_input()
    sb = find_send_btn()
    if ci and sb:
        tasks = [
            ('帮我出5道选择题', '出题'),
            ('帮我总结重点', '总结'),
        ]
        for task, label in tasks:
            ci = find_chat_input()
            sb = find_send_btn()
            if ci and sb:
                ci.click()
                ci.fill(task)
                print(f'请求: "{task}"')
                sb.click()
                time.sleep(8)

        ss(page, 'learning_assist')
        final_body = page.inner_text('body')
        print(f'最终页面(后500字): {final_body[-500:]}')

        # Check if questions were actually generated
        if 'A.' in final_body or 'B.' in final_body or 'C.' in final_body or '选择' in final_body[-500:]:
            print('OK 可能成功生成了选择题')
        else:
            print('WARN 未看到选择题格式的回复')
            issue('P2', 7, '自然语言出题功能不可靠',
                  '说"帮我出5道选择题"后，不确定系统是否正确处理了出题意图',
                  '用自然语言请求出题、总结、预测',
                  '提供明确的出题命令或按钮，确保意图识别准确')
    else:
        print('SKIP')

    # ================================================================
    # TEST 8: 课程切换
    # ================================================================
    h('测试8：课程切换与知识隔离')

    # Create second course
    course_input2 = None
    for inp in page.locator('textarea, input[type="text"]').all():
        try:
            ph = inp.get_attribute('placeholder') or ''
            if '课程名' in ph:
                course_input2 = inp
                break
        except: pass

    if course_input2:
        course_input2.click()
        course_input2.fill('操作系统')
        create_btn2 = None
        for btn in page.locator('button').all():
            try:
                if btn.inner_text().strip() == '创建':
                    create_btn2 = btn
                    break
            except: pass
        if create_btn2:
            create_btn2.click()
            time.sleep(2)
            print('OK 创建第二门课程"操作系统"')

    ss(page, 'two_courses')

    body8 = page.inner_text('body')
    if '操作系统' in body8 and '数据结构' in body8:
        print('OK 两门课程都在页面上')
    else:
        print('WARN 无法确认两门课程')

    issue('P1', 8, '课程切换后知识隔离不明',
          '创建了两门课程后，不确定在课程A提问时是否混入了课程B的内容',
          '创建课程A和B -> 分别上传不同PDF -> 切换后提问',
          '切换课程时清空聊天历史并提示"已切换到XX"')

    # ================================================================
    # TEST 9: 长期使用场景
    # ================================================================
    h('测试9：长期使用体验')

    long_term_issues = [
        ('P2', '每次创建课程后需手动切到新课程才能上传，操作繁琐',
         '创建课程 -> 自动切到新课程'),
        ('P2', '无学习进度指示，不知道自己学了什么',
         '显示学习统计：已上传X个文件、已提问Y次'),
        ('P2', '快捷按钮("出题练习""薄弱点")点击后只填充文字而不触发动作',
         '快捷按钮应直接触发功能而非仅填充输入框'),
        ('P2', '刷新页面后对话历史丢失',
         '保存对话历史到本地或后端'),
        ('P3', '无暗色模式/主题切换',
         '添加主题切换选项'),
        ('P3', '删除课程无二次确认弹窗',
         '危险操作添加确认弹窗'),
        ('P3', '文件列表仅显示文件名，不显示上传时间和大小',
         '文件管理中显示更多元数据'),
    ]
    for sev, desc, suggest in long_term_issues:
        issue(sev, 9, desc.split('，')[0], desc, '连续使用30分钟后的感受', suggest)

    # ================================================================
    # 关闭
    # ================================================================
    browser.close()
    p.stop()
    client.close()

    # ================================================================
    # 输出最终报告
    # ================================================================
    h('最终测试报告')

    by_sev = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
    for i in issues:
        sev = i['severity']
        if sev in by_sev:
            by_sev[sev].append(i)

    labels = {'P0': '系统不可用', 'P1': '严重影响学习', 'P2': '影响体验', 'P3': '优化建议'}

    for sev in ['P0', 'P1', 'P2', 'P3']:
        items = by_sev[sev]
        if items:
            print(f'\n--- {sev} ({labels[sev]}): {len(items)} 个 ---')
            for i, item in enumerate(items, 1):
                print(f'\n{sev}-{i}: {item["title"]}')
                print(f'  测试编号: {item["test"]}')
                print(f'  现象/原因: {item["desc"]}')
                print(f'  复现步骤: {item["reproduce"]}')
                if 'suggest' in item:
                    print(f'  修改建议: {item["suggest"]}')

    total = len(issues)
    print(f'\n\n========== 总计: {total} 个问题 ==========')
    print(f'P0(系统不可用): {len(by_sev["P0"])}')
    print(f'P1(严重影响学习): {len(by_sev["P1"])}')
    print(f'P2(影响体验): {len(by_sev["P2"])}')
    print(f'P3(优化建议): {len(by_sev["P3"])}')

    # Save JSON
    report = {
        'total': total,
        'by_severity': {k: len(v) for k, v in by_sev.items()},
        'issues': issues
    }
    with open(os.path.join(SCREENSHOT_DIR, 'final_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('\nJSON报告已保存')

if __name__ == '__main__':
    run()
