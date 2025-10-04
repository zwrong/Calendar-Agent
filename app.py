from flask import Flask, render_template, request, jsonify

from calendar_agent_deepseek import CalendarAgentDeepSeek

app = Flask(__name__)

# Initialize the calendar agent
try:
    agent = CalendarAgentDeepSeek()
    agent_ready = True
except Exception as e:
    print(f"Agent initialization failed: {e}")
    agent_ready = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/command', methods=['POST'])
def process_command():
    if not agent_ready:
        return jsonify({
            'success': False,
            'message': '日历代理未初始化，请检查环境变量配置'
        })

    data = request.get_json()
    user_input = data.get('command', '').strip()
    selected_calendar = data.get('calendar', None)

    if not user_input:
        return jsonify({
            'success': False,
            'message': '请输入有效的指令'
        })

    try:
        response = agent.process_command(user_input, selected_calendar)
        return jsonify({
            'success': True,
            'message': response
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理指令时出现错误: {str(e)}'
        })

@app.route('/api/calendars')
def get_calendars():
    if not agent_ready:
        return jsonify({
            'success': False,
            'message': '日历代理未初始化'
        })

    try:
        calendars = agent.get_calendar_list()
        return jsonify({
            'success': True,
            'calendars': calendars,
            'message': agent.get_calendar_list_formatted()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取日历列表失败: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)