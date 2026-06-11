// Echo 学习助手 - 真实大学生用户测试
// 使用 Playwright 进行端到端用户测试

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = 'http://127.0.0.1:7863';
const SCREENSHOT_DIR = 'E:/echo/test_screenshots';

// Helper
let stepNum = 0;
async function ss(page, label) {
    stepNum++;
    const name = `${String(stepNum).padStart(2, '0')}_${label}.png`;
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, name), fullPage: true });
    console.log(`  📸 ${name}`);
    return name;
}

function log(msg) { console.log(`  ${msg}`); }
function h1(msg) { console.log(`\n${'='.repeat(60)}\n${msg}\n${'='.repeat(60)}`); }
function h2(msg) { console.log(`\n--- ${msg} ---`); }

async function waitAndLog(page, text, ms=500) {
    await page.waitForTimeout(ms);
    log(text);
}

// ================================================================
// 测试9：长期使用场景（提前做，因为测试过程中就能感受到）
function longTermObservations() {
    const observations = [];
    h1('测试9：长期使用体验观察（测试过程中的感受）');
    observations.push('整个测试过程中，每做一步都要切换到不同操作区域');
    return observations;
}

// ================================================================
async function run() {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();

    let issues = []; // 收集所有问题

    try {
        // ==========================================
        // 测试1：首次使用体验
        // ==========================================
        h1('测试1：首次使用体验');

        await page.goto(BASE);
        await page.waitForLoadState('networkidle');
        await waitAndLog(page, '页面已加载');
        await ss(page, 'test1_first_impression');

        // 获取页面文字
        const bodyText = await page.innerText('body');
        console.log('\n【页面可见文字内容】');
        console.log(bodyText.substring(0, 3000));
        console.log('...\n');

        // 回答测试1问题
        h2('测试1 回答');

        // Q1: 知道系统是干什么的吗？
        log('Q1: 我知道这个系统是干什么的吗？');
        if (bodyText.includes('学习') || bodyText.includes('课程')) {
            log('  → 大概知道是"学习助手"，但具体能做什么不够明确');
            issues.push({test: 1, severity: 'P2', title: '首页缺少明确的功能说明',
                desc: '标题是"大学课程学习助手"，但没有一句话说清楚系统能做什么。学生需要猜测。',
                reproduce: '打开系统首页，阅读页面文字', suggest: '在标题下方增加一行简短的功能说明，如"上传课程资料，AI帮你总结、出题、答疑"'});
        }
        if (!bodyText.includes('怎么') && !bodyText.includes('步骤') && !bodyText.includes('开始')) {
            log('  → 没有操作引导');
            issues.push({test: 1, severity: 'P1', title: '完全没有新手引导',
                desc: '一个大二学生第一次打开这个页面，没有任何步骤指引告诉他第一步该做什么。',
                reproduce: '以新用户身份首次打开系统', suggest: '添加新手引导：Step 1 创建课程 → Step 2 上传资料 → Step 3 开始提问'});
        }

        // Q2: 第一步该做什么？
        log('Q2: 我知道第一步该做什么吗？');
        // Check for clear primary action
        if (bodyText.includes('新建课程') && bodyText.includes('输入课程名')) {
            log('  → 看到"新建课程"输入框，但不明显');
        }
        if (!bodyText.includes('请先') && !bodyText.includes('第一步')) {
            log('  → 没有明确指示第一步操作');
            issues.push({test: 1, severity: 'P1', title: '不知道第一步该做什么',
                desc: '页面同时展示了课程下拉框、新建课程输入框、欢迎文本、聊天输入框，学生不知道该先做什么。',
                reproduce: '首次打开页面，观察30秒', suggest: '使用步骤引导或突出高亮当前最重要操作'});
        }

        // Q3: 能否独立开始使用？
        log('Q3: 如果没有任何说明，我能独立开始使用吗？');
        log('  → 大概率不能。界面元素散乱，需要自己摸索。');

        // Q4: 哪些地方让我困惑？
        log('Q4: 哪些地方让我困惑？');
        log('  → 困惑点：顶部工具栏+欢迎区+底部输入框的关系不清楚');
        log('  → 困惑点："全部"是什么意思？是"全部课程"还是"全部内容"？');
        log('  → 困惑点：欢迎区提示可以输入问题，但还没上传资料，输入问题有用吗？');

        // ==========================================
        // 测试2：课程创建
        // ==========================================
        h1('测试2：课程创建');

        // Try to find course creation input
        const courseInputSelector = 'input[type="text"], input:not([type]), textarea';
        const allInputs = await page.locator(courseInputSelector).all();
        log(`找到 ${allInputs.length} 个输入框`);

        // 找到新建课程输入框
        let newCourseInput = null;
        for (const input of allInputs) {
            const placeholder = await input.getAttribute('placeholder');
            const label = await input.getAttribute('aria-label');
            log(`  输入框 placeholder="${placeholder}" aria-label="${label}"`);
            if (placeholder && placeholder.includes('课程名')) {
                newCourseInput = input;
                break;
            }
        }

        // 尝试所有输入框
        if (!newCourseInput) {
            log('  ⚠ 没有找到"新建课程"输入框，尝试所有可见输入框');
            // 找第二个文本输入框（第一个可能是聊天输入）
            if (allInputs.length >= 2) {
                newCourseInput = allInputs[1]; // 猜测第二个是课程名输入
            } else if (allInputs.length >= 1) {
                newCourseInput = allInputs[0];
            }
        }

        if (newCourseInput) {
            await newCourseInput.click();
            await newCourseInput.fill('数据结构');
            log('✅ 输入课程名"数据结构"');
            await ss(page, 'test2_course_name_entered');

            // 找创建按钮
            const buttons = await page.locator('button').all();
            let createBtn = null;
            for (const btn of buttons) {
                const text = await btn.innerText();
                if (text.includes('创建') || text.includes('新建')) {
                    createBtn = btn;
                    break;
                }
            }

            if (createBtn) {
                await createBtn.click();
                log('✅ 点击"创建"按钮');
                await page.waitForTimeout(1500);
                await ss(page, 'test2_course_created');

                // 检查是否有反馈
                const updatedText = await page.innerText('body');
                if (updatedText.includes('数据结构')) {
                    log('✅ 课程创建似乎成功（页面上出现了"数据结构"）');
                } else {
                    log('⚠ 创建后没有明确反馈');
                    issues.push({test: 2, severity: 'P2', title: '创建课程后反馈不明显',
                        desc: '输入课程名点击创建后，没有明确的成功提示。学生不知道操作是否成功。',
                        reproduce: '输入课程名→点击创建→观察反馈', suggest: '创建成功后显示绿色提示"课程「数据结构」创建成功"'});
                }

                // Check if dropdown updated
                const dropdownText = await page.locator('select').first().innerText().catch(() => '');
                log(`下拉框内容: "${dropdownText}"`);
            } else {
                log('❌ 找不到"创建"按钮');
                issues.push({test: 2, severity: 'P0', title: '找不到创建课程按钮',
                    desc: '输入课程名后，不知道按哪个按钮提交。',
                    reproduce: '输入课程名后寻找提交按钮', suggest: '确保创建按钮可见且在输入框旁边'});
            }
        } else {
            log('❌ 找不到课程名输入框');
            issues.push({test: 2, severity: 'P0', title: '找不到新建课程入口',
                desc: '作为一个新用户，找不到在哪里输入新课名称。',
                reproduce: '打开首页后寻找新建课程入口', suggest: '确保新建课程输入框有明确标签'});
        }

        // ==========================================
        // 测试3：上传课程资料
        // ==========================================
        h1('测试3：上传课程资料');

        // 检查是否有文件上传按钮
        const fileInputs = await page.locator('input[type="file"]').all();
        log(`文件上传输入框数量: ${fileInputs.length}`);

        // 查找上传相关的按钮
        const uploadBtns = [];
        for (const btn of buttons) {
            const text = await btn.innerText();
            if (text.includes('上传') || text.includes('文件') || text.includes('📎')) {
                uploadBtns.push({btn, text});
            }
        }
        log(`找到上传相关按钮: ${uploadBtns.length}`);
        uploadBtns.forEach(b => log(`  "${b.text}"`));

        // 尝试上传
        if (fileInputs.length > 0) {
            const pdfPath = 'E:/echo/data/pdfs/test.pdf';
            await fileInputs[0].setInputFiles(pdfPath);
            log('✅ 选择了 test.pdf 文件');
            await page.waitForTimeout(3000);
            await ss(page, 'test3_after_upload');

            const uploadText = await page.innerText('body');
            if (uploadText.includes('成功') || uploadText.includes('完成') || uploadText.includes('已上传')) {
                log('✅ 看到上传完成提示');
            } else {
                log('⚠ 上传后没有明确提示');
                issues.push({test: 3, severity: 'P1', title: '上传PDF后无反馈',
                    desc: '选择PDF文件后，不知道上传是否成功、系统是否已经开始处理。学生可能会重复上传。',
                    reproduce: '点击上传→选择PDF→观察反馈', suggest: '上传后显示进度条和处理状态'});
            }
        } else {
            log('❌ 找不到文件上传入口');
            issues.push({test: 3, severity: 'P0', title: '找不到文件上传入口',
                desc: '作为一个想上传课件的学生，找不到从哪里上传文件。',
                reproduce: '打开页面后寻找上传入口', suggest: '确保文件上传按钮有明确标识和位置'});
        }

        // ==========================================
        // 测试4：知识问答
        // ==========================================
        h1('测试4：知识问答');

        // 找到聊天输入框和发送按钮
        const chatInputs = await page.locator('input[type="text"], textarea').all();
        let chatInput = null;
        for (const input of chatInputs) {
            const ph = await input.getAttribute('placeholder');
            if (ph && (ph.includes('问题') || ph.includes('输入') || ph.includes('问题') || ph.includes('人话'))) {
                chatInput = input;
                break;
            }
        }
        if (!chatInput && chatInputs.length > 0) {
            chatInput = chatInputs[chatInputs.length - 1]; // 最后一个通常是聊天输入
        }

        if (chatInput) {
            await chatInput.click();
            await chatInput.fill('总结第一章内容');
            log('✅ 输入问题："总结第一章内容"');
            await ss(page, 'test4_question_entered');

            // 找发送按钮
            let sendBtn = null;
            const sendButtons = await page.locator('button').all();
            for (const btn of sendButtons) {
                const text = await btn.innerText();
                if (text.includes('发送') || text.includes('提交') || text.includes('Send')) {
                    sendBtn = btn;
                    break;
                }
            }

            if (sendBtn) {
                await sendBtn.click();
                log('✅ 点击发送');
                await page.waitForTimeout(5000); // 等待AI回答
                await ss(page, 'test4_answer_received');

                const answerText = await page.innerText('body');
                log(`回答内容（截取前500字）:\n${answerText.substring(answerText.indexOf('总结') || 0, 500)}`);

                // 检查是否引用了课程资料
                if (answerText.includes('第一章') || answerText.includes('第1章') || answerText.includes('test.pdf')) {
                    log('✅ 回答似乎引用了课程资料');
                } else {
                    log('⚠ 不确定是否引用了课程资料');
                    issues.push({test: 4, severity: 'P1', title: '回答未明确标注引用来源',
                        desc: '学生无法区分回答是基于课程资料还是AI自己编的。',
                        reproduce: '提问关于课程内容的问题', suggest: '回答中明确标注引用来源文件名和章节'});
                }
            } else {
                log('❌ 找不到发送按钮');
                issues.push({test: 4, severity: 'P0', title: '找不到发送按钮',
                    desc: '输入问题后，找不到发送按钮。',
                    reproduce: '在聊天输入框输入文字', suggest: '确保发送按钮在输入框附近且可见'});
            }
        } else {
            log('❌ 找不到聊天输入框');
            issues.push({test: 4, severity: 'P0', title: '找不到聊天输入框',
                desc: '想提问但不知道在哪里输入。',
                reproduce: '打开页面后找提问区域', suggest: ''});
        }

        // ==========================================
        // 测试5：追问能力
        // ==========================================
        h1('测试5：追问能力');

        if (chatInput) {
            const followUps = ['举个例子', '详细解释第三点', '我没理解，再解释一次'];
            for (const q of followUps) {
                await chatInput.click();
                await chatInput.fill(q);
                log(`追问: "${q}"`);

                if (sendBtn) {
                    await sendBtn.click();
                    await page.waitForTimeout(4000);
                }
            }
            await ss(page, 'test5_followup');
            log('⚠ 无法确认系统是否保留了上下文（需要人工判断回答质量）');
            issues.push({test: 5, severity: 'P2', title: '追问上下文保持不明确',
                desc: '连续提问后，无法确认系统是否理解当前讨论的上下文。如果丢失上下文，会严重影响学习连贯性。',
                reproduce: '连续提问3轮追问', suggest: '在回答中保持上下文标识'});
        }

        // ==========================================
        // 测试6：错误场景
        // ==========================================
        h1('测试6：错误场景 - 提问无关内容');

        if (chatInput && sendBtn) {
            await chatInput.click();
            await chatInput.fill('量子力学是什么？');
            await sendBtn.click();
            await page.waitForTimeout(5000);
            await ss(page, 'test6_out_of_scope');

            const bodyAfter = await page.innerText('body');
            if (bodyAfter.includes('不知道') || bodyAfter.includes('未找到') || bodyAfter.includes('暂无') || bodyAfter.includes('无法')) {
                log('✅ 系统承认不知道或无法回答');
            } else if (bodyAfter.includes('量子')) {
                log('⚠ 系统可能胡编了量子力学的内容');
                issues.push({test: 6, severity: 'P1', title: '系统可能对无关问题胡编乱造',
                    desc: '提问课程资料中不存在的内容时，系统如果不拒绝回答而是胡编，会严重误导学生学习。',
                    reproduce: '上传的课程资料里没有量子力学，然后问"量子力学是什么？"',
                    suggest: '当检索不到相关内容时，明确告知"您的课程资料中没有相关的内容"并拒绝编造'});
            }
        }

        // ==========================================
        // 测试7：学习辅助能力
        // ==========================================
        h1('测试7：学习辅助功能');

        if (chatInput && sendBtn) {
            const learningTasks = [
                '帮我出5道选择题',
                '帮我总结重点',
                '预测考试可能考什么',
            ];

            for (const task of learningTasks) {
                await chatInput.click();
                await chatInput.fill(task);
                await sendBtn.click();
                log(`请求: "${task}"`);
                await page.waitForTimeout(5000);
            }
            await ss(page, 'test7_learning_assist');
            log('⚠ 学习辅助功能需人工判断回答质量');
            issues.push({test: 7, severity: 'P2', title: '学习辅助功能可用性存疑',
                desc: '出题、总结、考试预测等功能的自然语言触发是否可靠？学生不知道哪些命令有效。',
                reproduce: '尝试用自然语言请求学习辅助功能',
                suggest: '提供明确的命令列表或快捷按钮'});
        }

        // ==========================================
        // 测试8：课程切换
        // ==========================================
        h1('测试8：课程切换');

        // 先尝试创建第二门课程
        if (newCourseInput) {
            await newCourseInput.click();
            await newCourseInput.fill('线性代数');
            if (createBtn) {
                await createBtn.click();
                await page.waitForTimeout(1000);
                log('✅ 创建第二门课程"线性代数"');
            }
        }

        // 尝试切换课程
        const dropdowns = await page.locator('select').all();
        if (dropdowns.length > 0) {
            const courseDropdown = dropdowns[0];
            await courseDropdown.selectOption({ label: '数据结构' });
            await page.waitForTimeout(500);
            log('切换到"数据结构"');

            // 提问
            if (chatInput && sendBtn) {
                await chatInput.fill('总结一下课程');
                await sendBtn.click();
                await page.waitForTimeout(3000);
            }

            // 切换到另一门
            await courseDropdown.selectOption({ label: '线性代数' });
            await page.waitForTimeout(500);
            log('切换到"线性代数"');

            if (chatInput && sendBtn) {
                await chatInput.fill('总结一下课程');
                await sendBtn.click();
                await page.waitForTimeout(3000);
            }
            await ss(page, 'test8_course_switch');

            log('⚠ 无法确认是否有知识串线');
            issues.push({test: 8, severity: 'P1', title: '课程切换后可能知识串线',
                desc: '切换课程后提问，不知道系统是否真的切换了知识库。学生可能获得错误的课程内容。',
                reproduce: '课程A上传课件→提问→切换到课程B→提问相似问题',
                suggest: '切换课程时清空对话历史，并明确提示已切换到哪个课程'});
        }

    } catch (error) {
        console.error('测试异常:', error.message);
    } finally {
        await browser.close();
        console.log('\n\n✅ 浏览器已关闭。截图保存在 test_screenshots/ 目录');
    }

    // ==========================================
    // 输出汇总
    // ==========================================
    h1('测试报告汇总');

    const bySeverity = {P0: [], P1: [], P2: [], P3: []};
    issues.forEach(i => {
        if (!bySeverity[i.severity]) bySeverity[i.severity] = [];
        bySeverity[i.severity].push(i);
    });

    console.log(`\n共发现 ${issues.length} 个问题\n`);

    ['P0', 'P1', 'P2', 'P3'].forEach(sev => {
        const items = bySeverity[sev];
        if (items.length > 0) {
            const label = sev === 'P0' ? '系统不可用' : sev === 'P1' ? '严重影响学习' : sev === 'P2' ? '影响体验' : '优化建议';
            console.log(`--- ${sev} (${label}): ${items.length} 个 ---`);
            items.forEach((item, idx) => {
                console.log(`\n${sev}-${idx+1}: ${item.title}`);
                console.log(`  原因: ${item.desc}`);
                console.log(`  复现: ${item.reproduce}`);
                console.log(`  建议: ${item.suggest}`);
            });
        }
    });

    return issues;
}

run().then(issues => {
    console.log('\n测试完成！');
}).catch(err => {
    console.error('测试失败:', err);
    process.exit(1);
});
