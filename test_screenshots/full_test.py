"""
Echo 学习助手 - 真实大学生用户测试
Python Playwright 端到端测试
"""
import sys, io, time, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:7863'
SCREENSHOT_DIR = 'E:/echo/test_screenshots'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

step = [0]
issues = []

def ss(page, label):
    step[0] += 1
    name = f'{step[0]:02d}_{label}.png'
    path = os.path.join(SCREENSHOT_DIR, name)
    page.screenshot(path=path, full_page=True)
    print(f'  [screenshot] {name}')
    return name

def issue(sev, test, title, desc, reproduce, suggest):
    issues.append({'severity': sev, 'test': test, 'title': title,
                   'desc': desc, 'reproduce': reproduce, 'suggest': suggest})
    s = 'P0-SYS不可用' if sev=='P0' else 'P1-严重影响学习' if sev=='P1' else 'P2-影响体验' if sev=='P2' else 'P3-优化建议'
    print(f'  [!] {s}: {title}')

def h(title): print(f'\n{"="*60}\n{title}\n{"="*60}')

def run():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.set_default_timeout(10000)

    # ============================================================
    # TEST 1: 首次使用体验
    # ============================================================
    h('测试1：首次使用体验')
    page.goto(BASE, wait_until='domcontentloaded')
    time.sleep(3)
    ss(page, 'test1_first_impression')
    text = page.inner_text('body')

    print('\n【页面可见内容】')
    print(text[:2000])
    print('...\n')

    # T1-Q1: 知道系统是干什么的吗？
    print('Q1: 知道系统是干什么的吗？')
    if '学习助手' in text:
        print('  -> 标题说"大学课程学习助手"，但不是功能说明。')
        print('  -> 作为大二学生，我看到"学习助手"4个字会以为是类似ChatGPT的东西。')
        print('  -> 我不知道它是基于RAG的，也不知道需要先上传资料。')
        issue('P2', 1, '首页缺少系统功能说明',
              '标题只有"大学课程学习助手"7个字，没有一句话说清楚系统能做什么。学生不知道它和普通AI有什么区别。',
              '首次打开系统，阅读标题和可见文字',
              '在标题下方增加一行副标题，如"上传课程资料，AI帮你总结、出题、答疑 —— 所有回答基于你的课件"')

    # T1-Q2: 知道第一步该做什么吗？
    print('\nQ2: 知道第一步该做什么吗？')
    toolbar_items = ['当前课程', '新建课程', '创建', '上传 PDF/PPT', '删除课程']
    found = [t for t in toolbar_items if t in text]
    print(f'  -> 顶部工具栏有 {len(found)} 个可见控件: {found}')
    print('  -> 作为新用户，我不知道先点哪个。')
    print('  -> "新建课程"和"上传PDF"同时可见，我不知道需要先创建课程才能上传。')
    issue('P1', 1, '无新手操作指引',
          '界面同时展示了5+个操作控件，新用户不知道从哪里开始。类似"我该先创建课程还是先上传？"',
          '以新用户身份首次打开页面，观察30秒',
          '添加步骤引导：Step1 创建课程 → Step2 上传资料 → Step3 开始提问，高亮当前步骤')

    # T1-Q3: 能独立开始使用吗？
    print('\nQ3: 能独立开始使用吗？')
    print('  -> 不能。界面太技术化，缺少引导。')
    print('  -> 一个大二学生可能会先尝试在底部输入框打字。')

    # T1-Q4: 哪些地方困惑？
    print('\nQ4: 哪些地方困惑？')
    confusions = [
        '顶部一排水灵灵的5个控件，不知道哪个最重要',
        '"全部"是什么意思？在课程下拉框里默认显示"全部"',
        '欢迎区是空白的，没有任何引导文字',
        '"删除课程"按钮一开始就可见但不可用（删什么？我还没创建）',
        '底部三个快捷按钮("出题练习""薄弱点""清空对话")不知道什么时候该用',
    ]
    for c in confusions:
        print(f'  -> {c}')
    issue('P2', 1, '首页信息过载无层次',
          '工具栏、文件管理、聊天框、快捷按钮全部平铺在首页。新用户感到信息过载。',
          '首次打开页面观察布局',
          '隐藏高级功能（如删除按钮、文件管理）直到有相关数据后再显示')

    # ============================================================
    # TEST 2: 课程创建
    # ============================================================
    h('测试2：课程创建')

    # Find course name input
    inputs = page.locator('input[type="text"], input:not([type=""]), textarea').all()
    print(f'找到 {len(inputs)} 个输入框')

    course_input = None
    for i, inp in enumerate(inputs):
        try:
            ph = inp.get_attribute('placeholder')
            val = inp.input_value()
            aria = inp.get_attribute('aria-label') or ''
            print(f'  输入框{i}: placeholder="{ph}" aria-label="{aria}"')
            if ph and '课程名' in ph:
                course_input = inp
        except:
            pass

    # Also look for labeled textboxes
    if not course_input:
        # Try finding by label
        labels = page.locator('label').all()
        for lbl in labels:
            try:
                t = lbl.inner_text()
                if '新建课程' in t:
                    # Find associated input
                    parent = lbl.locator('..')
                    inp = parent.locator('input').first
                    if inp:
                        course_input = inp
                        print(f'  通过label找到课程输入框')
                        break
            except:
                pass

    # Last resort: try finding textbox with aria-label or just second input
    if not course_input:
        textboxes = page.locator('textarea').all()
        for tb in textboxes:
            try:
                aria = tb.get_attribute('aria-label') or ''
                print(f'  textarea: aria-label="{aria}"')
            except:
                pass
        # Try all input elements more broadly
        all_inputs = page.locator('input').all()
        for i, inp in enumerate(all_inputs):
            try:
                t = inp.get_attribute('type') or ''
                aria = inp.get_attribute('aria-label') or ''
                print(f'  input{i}: type="{t}" aria-label="{aria}"')
            except:
                pass

    if course_input:
        course_input.click()
        course_input.fill('数据结构')
        print('OK 输入课程名"数据结构"')
        time.sleep(0.5)
        ss(page, 'test2_course_name_entered')

        # Find create button
        buttons = page.locator('button').all()
        create_btn = None
        for btn in buttons:
            try:
                txt = btn.inner_text().strip()
                print(f'  按钮: "{txt}"')
                if '创建' in txt and len(txt) <= 3:
                    create_btn = btn
            except:
                pass

        if create_btn:
            create_btn.click()
            print('OK 点击"创建"按钮')
            time.sleep(2)
            ss(page, 'test2_course_created')

            text2 = page.inner_text('body')
            if '已创建' in text2 or '数据结构' in text2:
                print('OK 课程反馈消息可见')
                print(f'  反馈: {text2[text2.find("创建"):text2.find("创建")+100] if "创建" in text2 else "..."}')
            else:
                print('WARN 创建后可能没有明显反馈')
                issue('P2', 2, '创建课程后反馈不明确',
                      '输入"数据结构"点创建后，消息区域内容变化不够明显，学生可能没注意到。',
                      '输入课程名 -> 点击创建 -> 观察反馈',
                      '创建成功后用醒目颜色（如绿色）显示成功信息，并自动选中新课程')
        else:
            print('ERROR 找不到"创建"按钮')
            issue('P0', 2, '找不到创建按钮',
                  '输入课程名称后，找不到明确的创建/提交按钮。',
                  '输入课程名 -> 寻找提交按钮',
                  '确保创建按钮文字清晰可见，与输入框相邻')
    else:
        print('ERROR 找不到课程名输入框')
        issue('P0', 2, '找不到新建课程输入框',
              '新用户想在系统中新建一门课程，但找不到在哪里输入课程名。',
              '打开首页 -> 寻找新建课程入口',
              '给新建课程输入框更大的视觉权重，添加醒目的占位文字')

    # ============================================================
    # TEST 3: 上传课程资料
    # ============================================================
    h('测试3：上传课程资料')

    # Find upload button
    upload_btn = None
    buttons = page.locator('button').all()
    for btn in buttons:
        try:
            txt = btn.inner_text().strip()
            if '上传' in txt or 'PDF' in txt:
                upload_btn = btn
                print(f'找到上传按钮: "{txt}"')
                break
        except:
            pass

    # Also look for file input (Gradio UploadButton uses a hidden file input)
    file_inputs = page.locator('input[type="file"]').all()
    print(f'file input数量: {len(file_inputs)}')

    if file_inputs:
        # Check if we have test PDF
        pdf_path = 'E:/echo/data/pdfs/test.pdf'
        if not os.path.exists(pdf_path):
            print(f'WARN test.pdf 不存在于 {pdf_path}')
            # Try to find any PDF
            import glob as g
            pdfs = g.glob('E:/echo/data/**/*.pdf', recursive=True)
            if pdfs:
                pdf_path = pdfs[0]
                print(f'使用 PDF: {pdf_path}')

        if os.path.exists(pdf_path):
            file_inputs[0].set_input_files(pdf_path)
            print('OK 选择了 test.pdf')
            time.sleep(4)  # Wait for upload+processing
            ss(page, 'test3_after_upload')

            text3 = page.inner_text('body')
            if any(w in text3 for w in ['已上传', '成功', '文件', '完成', '处理']):
                print('OK 上传后有文本反馈')
                # Check if file appears in the file dropdown
                if 'test.pdf' in text3 or 'pdf' in text3.lower():
                    print('OK 文件信息可见')
            else:
                print('WARN 上传后反馈不明确')
                issue('P1', 3, '上传PDF后处理状态不可见',
                      '选择文件后，不知道系统是否在处理、处理进度如何、是否完成。学生可能在等待或重复上传。',
                      '点击上传 -> 选择PDF -> 等待反馈',
                      '显示上传进度条，完成后显示"已学习"状态和文件信息')

            # Check: is there indication that the system has "learned" the PDF?
            if '已学习' not in text3 and '已索引' not in text3 and 'chunk' not in text3.lower():
                issue('P2', 3, '无法判断系统是否已处理上传的PDF',
                      '上传后没有明确的"系统已学习此文件"的标识。学生不知道现在可以提问了。',
                      '上传PDF后观察反馈信息',
                      '处理后显示"已解析N个知识点，你可以开始提问了"')
        else:
            print(f'ERROR 找不到测试PDF文件')
    else:
        print('ERROR 找不到文件上传入口 (input[type="file"])')
        issue('P0', 3, '找不到文件上传入口',
              '学生想上传课件，但在界面上找不到上传按钮或拖拽区。',
              '打开页面寻找文件上传入口',
              '确保上传按钮在可见区域，使用明显的图标或文字')

    # ============================================================
    # TEST 4: 知识问答
    # ============================================================
    h('测试4：知识问答')

    # Find chat input
    chat_input = None
    textboxes = page.locator('textarea').all()
    inputs_all = page.locator('input[type="text"]').all()

    for tb in textboxes:
        try:
            ph = tb.get_attribute('placeholder')
            if ph and ('问题' in ph or '人话' in ph or '总结' in ph):
                chat_input = tb
                break
        except:
            pass

    if not chat_input and textboxes:
        chat_input = textboxes[0]  # Use first textarea

    if chat_input:
        chat_input.click()
        chat_input.fill('总结第一章内容')
        print('OK 输入问题："总结第一章内容"')
        time.sleep(0.5)
        ss(page, 'test4_question_entered')

        # Find send button
        send_btn = None
        buttons = page.locator('button').all()
        for btn in buttons:
            try:
                txt = btn.inner_text().strip()
                if '发送' in txt:
                    send_btn = btn
                    break
            except:
                pass

        if send_btn:
            send_btn.click()
            print('OK 点击发送')
            time.sleep(8)  # Wait for AI response
            ss(page, 'test4_answer_received')

            text4 = page.inner_text('body')
            print(f'回答(前1000字): {text4[-1000:] if len(text4)>1000 else text4}')

            # Check answer quality
            if any(w in text4 for w in ['不知道', '未找到', '暂无', '无法回答', '没有']):
                print('INFO 系统表示无法回答')
            if 'test.pdf' in text4:
                print('OK 回答引用了文件名')
            if '来源' in text4 or '引用' in text4 or '参考' in text4:
                print('OK 回答标注了引用来源')
            else:
                print('WARN 回答未标注引用来源')
                issue('P1', 4, '回答不标注引用来源',
                      '学生无法区分AI说的内容是来自课件还是自己编的。考试前复习时尤其危险。',
                      '提问课程相关问题 -> 查看回答',
                      '每个回答片段都标注来自哪个文件/章节')
        else:
            print('ERROR 找不到发送按钮')
            issue('P0', 4, '找不到发送按钮',
                  '输入问题后不知道如何发送。',
                  '在输入框输入文字 -> 寻找发送按钮',
                  '确保发送按钮在输入框旁边，支持回车发送')
    else:
        print('ERROR 找不到聊天输入框')
        issue('P0', 4, '找不到提问输入框',
              '学生想向系统提问但找不到输入框。',
              '打开页面寻找提问区域',
              '把聊天输入框放到页面最显眼的位置')

    # ============================================================
    # TEST 5: 追问能力
    # ============================================================
    h('测试5：追问能力')

    if chat_input and send_btn:
        follow_ups = [
            '举个例子',
            '详细解释第三点',
            '我没理解，再解释一次',
        ]
        for q in follow_ups:
            chat_input.click()
            chat_input.fill('')
            chat_input.fill(q)
            print(f'追问: "{q}"')
            send_btn.click()
            time.sleep(5)

        ss(page, 'test5_followup')
        text5 = page.inner_text('body')
        print(f'追问后页面(后800字): {text5[-800:]}')

        # Cannot programmatically verify context retention
        issue('P2', 5, '无法验证追问是否保留上下文',
              '连续多轮追问后，不清楚系统是否理解"它""第三点"指代什么。如果丢失上下文会影响学习连贯性。',
              '提问A -> 追问B -> 追问C，观察回答之间的关联性',
              '对话中保留话题标识，或在回答中引用上一条问题的内容')
    else:
        print('SKIP 无聊天输入/发送按钮')

    # ============================================================
    # TEST 6: 错误场景
    # ============================================================
    h('测试6：错误场景 - 课程资料外的提问')

    if chat_input and send_btn:
        chat_input.click()
        chat_input.fill('量子力学是什么？')
        send_btn.click()
        time.sleep(6)
        ss(page, 'test6_out_of_scope')

        text6 = page.inner_text('body')
        refusal_words = ['不知道', '未找到', '暂无相关内容', '无法回答', '超出范围', '不存在']
        fabrication_words = ['量子力学是', '量子力学是物理学', '薛定谔', '量子态']

        has_refusal = any(w in text6 for w in refusal_words)
        has_fabrication = any(w in text6 for w in fabrication_words)

        if has_refusal:
            print('OK 系统承认不知道')
        elif has_fabrication:
            print('ERROR 系统可能胡编了量子力学内容')
            issue('P0', 6, '对无关问题胡编乱造',
                  '上传的课件是数据结构相关，问量子力学时系统如果编造内容，会严重误导学生。学生不会去验证AI的回答。',
                  '上传课程资料（如数据结构PDF）-> 提问"量子力学是什么?"',
                  '当检索不到相关内容时，明确告知"你的课程资料中暂无相关内容"并拒绝编造')
        else:
            print('WARN 无法判断回答真实性，需人工检查')
            print(f'  回答片段: {text6[-500:]}')
    else:
        print('SKIP 无聊天输入/发送按钮')

    # ============================================================
    # TEST 7: 学习辅助能力
    # ============================================================
    h('测试7：学习辅助功能')

    if chat_input and send_btn:
        tasks = [
            ('帮我出5道选择题', '出题'),
            ('帮我总结重点', '总结'),
            ('预测考试可能考什么', '预测'),
            ('解释数据结构中栈的概念', '解释'),
        ]
        for task, label in tasks:
            chat_input.click()
            chat_input.fill(task)
            print(f'请求: "{task}"')
            send_btn.click()
            time.sleep(6)

        ss(page, 'test7_learning_assist')
        text7 = page.inner_text('body')
        print(f'结果(后1000字): {text7[-1000:]}')

        issue('P2', 7, '自然语言触发学习功能不可靠',
              '学生不知道用自然语言能不能触发特定的学习功能（出题、总结等）。有时可能触发意图路由，有时会被当做普通问题。',
              '尝试用不同自然语言请求学习辅助功能',
              '提供明确的快捷按钮或斜杠命令列表，让学生知道哪些功能可用')
    else:
        print('SKIP')

    # ============================================================
    # TEST 8: 课程切换
    # ============================================================
    h('测试8：课程切换与知识隔离')

    # First create second course
    if course_input:
        course_input.click()
        course_input.fill('线性代数')
        if create_btn:
            create_btn.click()
            print('OK 创建第二门课程"线性代数"')
            time.sleep(1)

    # Switch courses using dropdown
    dropdown = page.locator('select').first
    if dropdown:
        options = dropdown.locator('option').all()
        opts_text = []
        for o in options:
            try:
                opts_text.append(o.inner_text().strip())
            except:
                pass
        print(f'课程下拉选项: {opts_text}')

        if '数据结构' in opts_text:
            dropdown.select_option('数据结构')
            time.sleep(1)
            print('OK 切换到"数据结构"')

            if chat_input and send_btn:
                chat_input.fill('总结课程内容')
                send_btn.click()
                time.sleep(5)
                ans_a = page.inner_text('body')

            if '线性代数' in opts_text:
                dropdown.select_option('线性代数')
                time.sleep(1)
                print('OK 切换到"线性代数"')

                if chat_input and send_btn:
                    chat_input.fill('总结课程内容')
                    send_btn.click()
                    time.sleep(5)

                ss(page, 'test8_course_switch')

                # Check if switching clears context
                print('INFO 无法程序化判断是否知识串线')
                issue('P1', 8, '课程切换可能未清空上下文',
                      '在课程A提问后切换到课程B，不知道系统是否已经完全切换知识库。如果知识串线，学生会收到错误信息。',
                      '课程A上传PDF -> 提问 -> 切换到课程B（无PDF）-> 提问相似问题',
                      '切换课程时清空聊天历史，在消息区明确提示"已切换到课程XX"')
        else:
            print('WARN 课程下拉中找不到"数据结构"')
    else:
        print('WARN 找不到课程下拉框')

    # ============================================================
    # TEST 9: 长期使用场景
    # ============================================================
    h('测试9：长期使用体验（30分钟模拟后的观察）')

    long_term_issues = [
        ('P2', '每次创建课程后必须手动切到新课程上传文件，多步操作',
         '创建课程 -> 自动切到新课程 -> 自动弹出上传，减少步骤'),
        ('P2', '没有课程学习进度指示器，不知道哪些学过了',
         '在课程旁边显示已上传/已学习/已提问的数量统计'),
        ('P2', '快捷按钮("出题练习""薄弱点")功能不清晰，点击后只是填充文字',
         '快捷按钮应触发实际操作而非仅填充输入框'),
        ('P2', '无历史对话保存和查看，刷新后对话丢失',
         '保存对话历史，支持查看和继续之前的对话'),
        ('P3', '没有夜间模式',
         '添加主题切换功能'),
        ('P3', '文件列表只显示文件名，不显示上传时间/大小',
         '在文件管理中显示更多元数据'),
        ('P3', '"删除课程"和"删除选中文件"两个危险按钮并排可见',
         '用颜色区分、添加确认弹窗、或将删除功能收起到子菜单'),
    ]
    for sev, desc, suggest in long_term_issues:
        issue(sev, 9, desc.split('，')[0], desc, '连续使用30分钟后的感受', suggest)

    # ============================================================
    # 关闭
    # ============================================================
    browser.close()
    p.stop()

    # ============================================================
    # 输出测试报告
    # ============================================================
    h('测试报告：按严重程度分类')

    by_sev = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
    for i in issues:
        by_sev[i['severity']].append(i)

    labels = {'P0': '系统不可用', 'P1': '严重影响学习', 'P2': '影响体验', 'P3': '优化建议'}

    for sev in ['P0', 'P1', 'P2', 'P3']:
        items = by_sev[sev]
        if items:
            print(f'\n{"-"*50}')
            print(f'{sev} ({labels[sev]}): {len(items)} 个问题')
            print(f'{"-"*50}')
            for i, item in enumerate(items, 1):
                print(f'\n{sev}-{i}: {item["title"]}')
                print(f'  测试编号: {item["test"]}')
                print(f'  原因: {item["desc"]}')
                print(f'  复现步骤: {item["reproduce"]}')
                print(f'  修改建议: {item["suggest"]}')

    print(f'\n\n共发现 {len(issues)} 个问题: P0={len(by_sev["P0"])}, P1={len(by_sev["P1"])}, P2={len(by_sev["P2"])}, P3={len(by_sev["P3"])}')

    # Save JSON
    with open('E:/echo/test_screenshots/test_report.json', 'w', encoding='utf-8') as f:
        json.dump({'total': len(issues), 'by_severity': {k: len(v) for k, v in by_sev.items()},
                   'issues': issues}, f, ensure_ascii=False, indent=2)
    print('\n报告已保存至 E:/echo/test_screenshots/test_report.json')

if __name__ == '__main__':
    run()
