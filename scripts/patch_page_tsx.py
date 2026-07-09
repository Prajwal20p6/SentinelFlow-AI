filepath = r'e:\SENTINELFLOW AI\frontend\src\app\page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the missing closing brace of fetchGovConfig
old_broken = """    } catch (err) {
      console.error('Fetch gov config error:', err);
    }
  const fetchPolicies = async () => {"""

new_fixed = """    } catch (err) {
      console.error('Fetch gov config error:', err);
    }
  };

  const fetchPolicies = async () => {"""

if old_broken in content:
    content = content.replace(old_broken, new_fixed, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed missing }; in fetchGovConfig')
else:
    print('ERROR: Pattern not found')
    idx = content.find("Fetch gov config error")
    print(repr(content[max(0,idx-50):idx+200]))
